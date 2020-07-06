import mysql.connector
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from hashids import Hashids
import requests
import smtplib, ssl
from flask import render_template, render_template_string, Markup, redirect, request, redirect, session, flash
from functools import wraps
from ftplib import FTP
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
from mixpanel import Mixpanel
import uuid
import pygal

mp = Mixpanel("b8d822e83104dca1bcf9bebf8cbd229b")

with open('config.json') as config_file:
    config = json.load(config_file)

dbhost = config['database']['host']
dbuser = config['database']['user']
dbpass = config['database']['password']
dbname = config['database']['database']

mailhost = config['mail']['host']
mailsender = config['mail']['sender']
mailpass = config['mail']['password']

hashkey = config['hashing']['key']
authsize = config['hashing']['auth_size']
salt = config['hashing']['salt']

fixer_api_token = config['xrate']['api_key']

ftp_user = config['ftp']['ftp_user']
ftp_pass = config['ftp']['ftp_pass']
ftp_host = config['ftp']['ftp_host']

def sendftp(filename, folder):
    ftp = FTP(ftp_host)
    try:
        ftp.login(user=ftp_user,passwd=ftp_pass)
        ftp.cwd(folder)
        ftp.storbinary('STOR '+filename, open(filename,'rb'))
        ftp.quit()
        return True
    except:
        return False

def set_token(string,authsize=authsize):
    hashid = Hashids(salt=salt, min_length=authsize)
    return hashid.encode(string)

def get_token(string,authsize=authsize):
    hashid = Hashids(salt=salt, min_length=authsize)
    ret = hashid.decode(string)[0]
    return ret

def create_alert():
    pass

def send_mail(subject, reciever, data, email_template='welcome'):
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = mailsender
    message["To"] = reciever 
    ret = render_template("emails/"+email_template+".html", data=data)
    part = MIMEText(ret,'html')
    message.attach(part)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(mailhost, 465, context=context) as server:
        server.login(mailsender, mailpass)
        server.sendmail(mailsender, reciever, message.as_string())
    return True

def db(sql, query='select'):
    conn = mysql.connector.connect(host=dbhost,user=dbuser, password=dbpass,database=dbname)
    cursor = conn.cursor(dictionary=True,buffered=True)
    ret = []
    cursor.execute(sql)
    if query == 'select':
        ret = cursor.fetchone()
    elif query == 'many':
        ret = cursor.fetchall()
    elif query == 'insert':
        ret = cursor.lastrowid
        conn.commit()
    elif query == 'update':
        conn.commit()
        ret = True
    cursor.close()
    return ret

def servdb(db, sql, query='select'):
    db = mysql.connector.connect(**db)
    cursor = db.cursor(dictionary=True,buffered=True)
    ret = []
    cursor.execute(sql)
    if query == 'select':
        ret = cursor.fetchone()
    elif query == 'many':
        ret = cursor.fetchall()
    elif query == 'insert':
        ret = cursor.lastrowid
        db.commit()
    elif query == 'update':
        db.commit()
        ret = True
    elif query == 'delete':
        db.commit()
        ret = True
    cursor.close()
    db.close()
    return ret

def next_billing(duration):
    return date.today() + relativedelta(months=+duration)

def alert(user_id,service_id,business_id,kind,link):
    alert_sql = "INSERT INTO `alert` \
        (`id`, `Date`, `user_id`, `service_id`, `business_id`, `Kind`, `Rating`, `Description`, `Link`, `Status`)\
             VALUES \
                 (NULL, current_timestamp(), "+str(user_id)+", "+str(service_id)+", "+str(business_id)+", '"+kind+"', '', '', '"+link+"', 0);"
    ret = db(alert_sql,'insert')
    return ret

def xrate(amount):
    if amount == 0 or amount == None:
        return 0
    to_currency = db('SELECT users.Currency FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))['Currency']
    sql = "SELECT `Amount` FROM `xrate` WHERE `ToCurrency` = '"+to_currency.replace(" ","")+"' ORDER BY `id` DESC LIMIT 0,1"
    fetch = db(sql,'select')
    if not fetch:
        return 0
    rate = fetch['Amount']
    amount = amount * int(rate)
    return amount

def login_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        ref = request.url
        if "user_id" not in session:
            return redirect('/auth/login?ref='+ref)
        else:
            user_id = get_token(session['user_id'])
            user_status = db('SELECT users.Status FROM '+dbname+'.users WHERE users.id = '+str(user_id),'select')['Status']
            alerts = db('SELECT alert.id, business.Name, service.Title, alert.Kind, alert.Status, alert.Date, alert.Link FROM '+dbname+'.alert LEFT JOIN '+dbname+'.service ON service.id = alert.service_id LEFT JOIN '+dbname+'.business ON business.id = alert.business_id WHERE alert.user_id = '+str(user_id)+' ORDER BY alert.id DESC LIMIT 0,3','many')
            session['alerts'] = alerts
            session['alert_badge'] = db('SELECT COUNT(*) AS "Total" FROM '+dbname+'.alert WHERE alert.Status = 0 AND alert.user_id = '+str(user_id))['Total']
            if user_status == 0:
                if 'auth/logout' not in ref:
                    return redirect('/auth/resend_email')
                else:
                    pass
            if request.script_root != '/business/add':
                counter = db('SELECT COUNT(*) as "Total" FROM '+dbname+'.business WHERE business.user_id = '+str(user_id))['Total']
                counter2 = db('SELECT COUNT(*) as "Total" FROM '+dbname+'.invites WHERE invites.sub_user = '+str(user_id))['Total']
                if (counter == 0) and (counter2 == 0):
                    return redirect('/business/add')
                else:
                    if 'select_biz' in session:
                        select_biz = session['select_biz']
                        if select_biz is not None:
                            pass
                        else:
                            sub_biz = db('SELECT invites.business_id as "id", business.Name FROM '+dbname+'.invites LEFT JOIN '+dbname+'.business ON business.id = invites.business_id WHERE invites.sub_user = '+str(user_id))
                            if sub_biz:
                                session['select_biz'] = sub_biz
                            else:
                                last_created = db('SELECT business.id, business.Name FROM '+dbname+'.business WHERE business.user_id = '+str(user_id)+' ORDER BY business.id DESC LIMIT 0,1')
                                session['select_biz'] = last_created
                        biz = db('SELECT business.id, business.Name FROM '+dbname+'.business WHERE business.user_id = '+str(user_id)+' AND business.id != '+str(select_biz['id']),'many')
                        invites = db('SELECT DISTINCT invites.business_id as "id", business.Name FROM '+dbname+'.invites LEFT JOIN '+dbname+'.business ON business.id = invites.business_id WHERE invites.sub_user = '+str(user_id)+' GROUP BY invites.business_id','many')
                        session['biz'] = biz
                        if invites:
                            for i in invites:
                                session['biz'].append(i)
                    else:
                        last_created = db('SELECT business.id, business.Name FROM '+dbname+'.business WHERE business.user_id = '+str(user_id)+' ORDER BY business.id DESC LIMIT 0,1')
                        session['select_biz'] = last_created
                        biz = db('SELECT business.id, business.Name FROM '+dbname+'.business WHERE business.user_id = '+str(user_id)+' AND business.id != '+str(session['select_biz']['id']),'many')
                        #invites = db('SELECT DISTINCT invites.business_id as "id", business.Name FROM '+dbname+'.invites LEFT JOIN '+dbname+'.business ON business.id = invites.business_id WHERE invites.sub_user = '+str(user_id)+' GROUP BY invites.business_id','many')
                        session['biz'] = biz
                        # if invites:
                        #     session['biz'].append(invites)
            else:
                pass
        if 'ref_code' in session:
            session.pop('ref_code')
            session.pop('unique_id')
        return f(*args, **kwargs)
    return decorated_function

def subscription(f,__plugin_name__):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        sub_id = request.args.get("sub_id","")
        if sub_id != '':
            sub_id = get_token(sub_id)
            sub = db('SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.id = '+str(sub_id),'select')
            service = db('SELECT * FROM '+dbname+'.service WHERE service.id = '+str(sub['service_id']),'select')
            status = sub['Status']
            token = sub['Token']
            session[service['config_file']] = token
            user_id = sub['user_id']
            if get_token(session['user_id']) == user_id:
                flash("The service youre trying to access is not assigned to your username")
                return redirect('/dashboard/business')
            if service['Kind'] == 'Free':
                if token == '':
                    return redirect('/'+service['config_file']+'/'+service['setup_url']+'?sub_id='+set_token(sub_id))
                else:
                    return f(*args, **kwargs)
            else:
                if status == 0:
                    return redirect('/dashboard/business?p=view&business_id='+str(sub['business_id']))
                elif status == 1:
                    if token == '':
                        return redirect('/'+service['config_file']+'/'+service['setup_url']+'?sub_id='+set_token(sub_id))
                    else:
                        return f(*args, **kwargs)
                elif status == 2:
                    return redirect('/dashboard/bills/renew?sub_id='+str(set_token(sub_id)))
                elif status == 3:
                    return f(*args, **kwargs)
        if __plugin_name__ in session:
            token = session[__plugin_name__]
            sub = db(f'SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.Token = "'+token+'"','select')
            if sub['Status'] == 0:
                return redirect("/dashboard/business?p=view&business_id="+str(set_token(sub['business_id'])))
            elif sub['Status'] == 1:
                return f(*args, **kwargs)
            elif sub['Status'] == 2:
                return redirect('/dashboard/bills/renew?sub_id='+str(set_token(sub['id'])))
            elif sub['Status'] == 3:
                return f(*args, **kwargs)
    return decorated_function
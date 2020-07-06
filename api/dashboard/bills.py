from flask import Blueprint, jsonify, request, session, flash, redirect, render_template
from . import *
from datetime import datetime

bills = Blueprint('bills','bills', url_prefix='/bills')

@bills.route("/",methods=['GET','POST'])
@login_required
def main_bills():
    billing = db("SELECT subscriptions.id, business.Name, service.Title, service.Category, `txref`,`Duration`,subscriptions.Amount,`Next_billing_date`,`Total_paid`,subscriptions.Date,subscriptions.Status FROM `subscriptions` LEFT JOIN "+dbname+".business ON business.id = subscriptions.business_id LEFT JOIN "+dbname+".service ON service.id = subscriptions.service_id WHERE subscriptions.user_id = "+str(get_token(session['user_id'])),'many')
    return render_template('dashboard/bills.html', page='', billing=billing)

@bills.route("/pay",methods=['GET','POST'])
@login_required
def pay():
    if request.method == 'POST':
        txref = request.form['txref']
        business_id = request.form['business_id']
        service_id = request.form['service_id']
        amount = request.form['amount']
        duration = request.form['duration']
        monthly = request.form['monthly']
        setup = request.form['setup']
        servicez = db('SELECT * FROM '+dbname+'.service WHERE service.id = '+str(get_token(service_id)),'select')
        if (servicez['Monthly'] == int(monthly)):
            sql = "INSERT INTO `subscriptions`(`id`, `user_id`, `business_id`, `service_id`, `txref`, `Duration`, `Amount`, `Setup_cost`, `Date`,`Status`) \
                VALUES (NULL,"+str(get_token(session['user_id']))+","+str(get_token(business_id))+","+str(get_token(service_id))+",'"+txref+"',"+str(duration)+","+str(amount)+","+str(setup)+",CURRENT_DATE(),0)"
            ret = db(sql,'insert')
            alert(get_token(session['user_id']),get_token(service_id),get_token(business_id),"Created Invoice","/bills/quotation/"+set_token(ret))
            profile = db('SELECT * FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))
            prof = {}
            prof['Name'] = profile['Name']
            prof['id'] = ret
            email = profile['Email']
            prof['Currency'] = profile['Currency']
            prof['Amount'] = xrate(amount)
            prof['Total'] = xrate(1.038*float(amount))
            prof['Fees'] = xrate(0.038*float(amount))
            prof['Monthly'] = xrate(int(monthly))
            prof['Business'] = db('SELECT business.Name FROM '+dbname+'.business WHERE business.id = '+str(get_token(business_id)))['Name']
            prof['Service'] = db('SELECT service.Title FROM '+dbname+'.service WHERE service.id = '+str(get_token(service_id)))['Title']
            send_mail('Invoice - Appfrican', email, prof, email_template='invoice')
            return jsonify({'status':'success','id':set_token(ret)}),200
        else:
            return jsonify({'status':'error'}),200
        pass
    else:
        sub_id = get_token(request.args.get('sub_id',''))
        sub = db('SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.id = '+str(sub_id))
        txref = sub['txref']
        data = {
            'txref': txref,
            'SECKEY': "FLWSECK-1a4d63b781b35309091ed9f886f8d152-X"
        }
        if sub['Status'] == 1:
            service_url = db('SELECT service.config_file FROM '+dbname+'.service WHERE service.id = '+str(sub['service_id']))['config_file']
            return redirect('/'+service_url+'?id='+str(set_token(sub['id'])))
        else:
            url = "https://api.ravepay.co/flwv3-pug/getpaidx/api/v2/verify"
            r = requests.post(url, data=data)
            response = json.loads(r.content)['data']
            if 'message' in response:
                if response['message'] == 'Transaction not found':
                    pass
                else:
                    pass
            else:
                if response['status'] == 'successful':
                    if response['chargecode'] == '00':
                        kind = db('SELECT service.Kind, service.Title FROM '+dbname+'.service WHERE service.id = '+str(sub['service_id']),'select')
                        if kind['Kind'] == 'Subscription':
                            duration = sub['Duration']
                            date = next_billing(duration)
                        total = response['amount']
                        sql = "UPDATE `subscriptions` SET `Response`='',subscriptions.Total_paid = "+str(total)+",`Status`= 1, subscriptions.Next_billing_date = '"+str(date)+"' WHERE subscriptions.id = " + str(sub_id)
                        db(sql,'update')
                        alert(get_token(session['user_id']),get_token(service_id),get_token(business_id),"Created Reciept","/bills/reciept/"+set_token(sub_id))
                        mp.people_track_charge(session['user_id'],sub['Amount'],{
                            '$time': datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                        })
                        return redirect('/business/view/'+set_token(sub["business_id"]))
                    else:
                        return redirect("/bills")
        servicez = db('SELECT * FROM '+dbname+'.service WHERE service.id = '+str(sub['service_id']),'select')
        profile = {}
        user = db('SELECT * FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))
        profile['email'] = user['Email']
        profile['txref'] = 'APP-'+str(uuid.uuid1().int)[:24]
        profile['business_id'] = session['select_biz']['id']
        profile['service_id'] = sub['service_id']
        profile['currency'] = user['Currency'].replace(" ","")
        return render_template('dashboard/bills.html', page='pay', sub=sub,profile=profile, servicez=servicez)

@bills.route("/verify",methods=['GET','POST'])
@login_required
def verify():
    sub_id = request.args.get("sub_id","")
    if sub_id != '':
        subscription = db('SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.id = '+ str(get_token(sub_id)),'select')
        data = {
            'txref': subscription['txref'],
            'SECKEY': "FLWSECK-1a4d63b781b35309091ed9f886f8d152-X"
        }
        if subscription['Status'] == 1:
            service_url = db('SELECT service.config_file FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']))['config_file']
            return redirect('/'+service_url+'?id='+str(set_token(subscription['id'])))
        else:
            url = "https://api.ravepay.co/flwv3-pug/getpaidx/api/v2/verify"
            r = requests.post(url, data=data)
            response = json.loads(r.content)['data']
            if 'message' in response:
                if response['message'] == 'Transaction not found':
                    return redirect("/bills")
                else:
                    return redirect("/bills")
            else:
                if response['status'] == 'successful':
                    if response['chargecode'] == '00':
                        kind = db('SELECT service.Kind, service.Title FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']),'select')['Kind']
                        if kind['Kind'] == 'Subscription':
                            duration = subscription['Duration']
                            date = next_billing(duration)
                        sql = "UPDATE `subscriptions` SET `Response`='',`Status`= 1, subscriptions.Next_billing_date = '"+str(date)+"' WHERE subscriptions.id = " + str(get_token(sub_id))
                        db(sql,'update')
                        profile = db('SELECT * FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))
                        prof = {}
                        amount = subscription['Amount']
                        monthly = db('SELECT service.Monthly FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']))['Monthly']
                        prof['Name'] = profile['Name']
                        email = profile['Email']
                        prof['Currency'] = profile['Currency']
                        prof['Amount'] = xrate(amount)
                        prof['Total'] = xrate(1.038*float(amount))
                        prof['Fees'] = xrate(0.038*float(amount))
                        prof['Monthly'] = xrate(monthly)
                        prof['Business'] = db('SELECT business.Name FROM '+dbname+'.business WHERE business.id = '+str(subscription['business_id']))['Name']
                        prof['Service'] = db('SELECT service.Title FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']))['Title']
                        #send_mail('Invoice - Appfrican', email, prof, email_template='reciept')
                        mp.track(session['user_id'], 'Payment', {
                            '$service': kind['Title'],
                            '$time': datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                        })
                        mp.people_track_charge(session['user_id'],subscription['Amount'],{
                            '$time': datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                        })
                        return redirect('/business/view/'+set_token(subscription["business_id"]))
                    else:
                        return redirect("/bills")
    else:
        return redirect('/bills')
    return render_template('dashboard/bills.html')

@bills.route("/renew",methods=['GET','POST'])
@login_required
def renew():
    p = request.args.get("p","")
    sub_id = request.args.get("sub_id","")
    if p == '':
        if request.method == 'POST':
            txref = request.form['txref']
            business_id = request.form['business_id']
            service_id = request.form['service_id']
            amount = request.form['amount']
            duration = request.form['duration']
            monthly = request.form['monthly']
            ref_id = get_token(request.form['ref_id'])
            totalpaid = request.form['totalpaid']
            service = db('SELECT * FROM '+dbname+'.service WHERE service.id = '+str(get_token(service_id)),'select')
            if service['Monthly'] == int(monthly):
                sql = "INSERT INTO `subscriptions`(`id`, `user_id`, `business_id`, `service_id`, `txref`, `Duration`, `Amount`, `Setup_cost`,subscriptions.Total_paid,subscriptions.Comment, `Date`,`Status`) \
                    VALUES (NULL,"+str(get_token(session['user_id']))+","+str(get_token(business_id))+","+str(get_token(service_id))+",'"+txref+"',"+str(duration)+","+str(amount)+",0,"+str(totalpaid)+",'"+str(ref_id)+"',CURRENT_DATE(),5)"
                ret = db(sql,'insert')
                return jsonify({'status':'success','id':set_token(ret)}),200
            else:
                return jsonify({'status':'error'}),200
            pass
        else:
            return render_template('dashboard/bills.html', page='renew',sub_id=sub_id) #add renew request
    elif p == 'verify':
        sub_id = request.args.get("sub_id","")
        if sub_id != '':
            subscription = db('SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.id = '+ str(get_token(sub_id)),'select')
            data = {
                'txref': subscription['txref'],
                'SECKEY': "FLWSECK-1a4d63b781b35309091ed9f886f8d152-X"
            }
            if subscription['Status'] == 1:
                service_url = db('SELECT service.config_file FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']))['config_file']
                return redirect('/'+service_url+'?id='+str(set_token(subscription['id'])))
            elif subscription['Status'] == 5:
                url = "https://api.ravepay.co/flwv3-pug/getpaidx/api/v2/verify"
                r = requests.post(url, data=data)
                response = json.loads(r.content)['data']
                if 'message' in response:
                    if response['message'] == 'Transaction not found':
                        return redirect("/bills")
                    else:
                        return redirect("/bills")
                else:
                    if response['status'] == 'successful':
                        if response['chargecode'] == '00':
                            ref_id = subscription['Comment']
                            kind = db('SELECT service.Kind FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']),'select')['Kind']
                            if kind == 'Subscription':
                                duration = subscription['Duration']
                                date = next_billing(duration)
                            sql = "UPDATE `subscriptions` SET `Response`='',`Status`= 1, subscriptions.Next_billing_date = '"+str(date)+"' WHERE subscriptions.id = " + str(ref_id)
                            db(sql,'update')
                            renew_url = db('SELECT service.renew_url FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']),'select')['renew_url']
                            flash("Your payment has been process successfully.","success")
                            service_name = db('SELECT service.Title FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']))['Title']
                            mp.track(session['user_id'], 'Renew', {
                                '$service': service_name,
                                '$time': datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                            })
                            mp.people_track_charge(session['user_id'],subscription['Amount'],{
                                '$time': datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                            })
                            if renew_url != '':
                                return redirect(renew_url)
                            return redirect('/business/view/'+set_token(subscription["business_id"]))
                        else:
                            return redirect("/bills")
        else:
            return redirect('dashboard/bills')
    return render_template('dashboard/bills.html')

@bills.route("/free",methods=['GET','POST'])
@login_required
def free():
    business_id = session['select_biz']['id']
    service_id = request.args.get("service_id","")
    user_id = session['user_id']
    amount = 0
    kind = db('SELECT service.Kind FROM '+dbname+'.service WHERE service.id = '+str(get_token(service_id)))['Kind']
    if kind != 'Free':
        return redirect('/business/view/'+str(set_token(business_id)))
    #check and ensure the service is free here
    currency = ''
    duration = ''
    sql = "INSERT INTO `subscriptions` \
    (`id`, `user_id`, `business_id`, `service_id`, `txref`, `Duration`, `Amount`, `Currency`, `Date`, `Comment`, `Response`, `Status`) VALUES \
        (NULL, '"+str(user_id)+"', '"+str(get_token(business_id))+"', '"+str(get_token(service_id))+"', '', '"+str(duration)+"', '"+str(amount)+"', '', current_timestamp(), '', '', '3');"
    ret = db(sql,'insert')
    config_file = db('SELECT service.config_file FROM '+dbname+'.service WHERE service.id = '+str(get_token(service_id)),'select')['config_file']
    if ret:
        return redirect('/'+config_file+'?sub_id='+set_token(ret))
    else:
        return redirect('/bills')

@bills.route("/cancel/<string:code>",methods=['GET','POST'])
@login_required
def cancel(code):
    if request.method == 'POST':
        mp.track(session['user_id'], 'Cancel Service', {
            'sub_id': code
        })
        #Set status to 5
        #Check for cancelation url and call it 
        return jsonify({'status':'success'})
    return render_template('dashboard/bills.html',page='cancel', sub_id=code)

@bills.route("/quotation/<string:code>",methods=['GET','POST'])
@login_required
def quoation(code):
    sub_id = get_token(code)
    subscription = db('SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.id = '+str(sub_id),'select')
    if subscription['Status'] == 1:
        return redirect("/bills/reciept/"+code)
    profile = db('SELECT * FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))
    prof = {}
    amount = subscription['Amount']
    monthly = db('SELECT service.Monthly FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']))['Monthly']
    prof['id'] = sub_id
    prof['Name'] = profile['Name']
    prof['Currency'] = profile['Currency']
    prof['Amount'] = xrate(amount)
    prof['Total'] = xrate(1.038*float(amount))
    prof['Fees'] = xrate(0.038*float(amount))
    prof['Monthly'] = xrate(monthly)
    prof['Business'] = db('SELECT business.Name FROM '+dbname+'.business WHERE business.id = '+str(subscription['business_id']))['Name']
    prof['Service'] = db('SELECT service.Title FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']))['Title']
    return render_template('emails/invoice.html', data=prof)

@bills.route("/reciept/<string:code>",methods=['GET','POST'])
@login_required
def reciept(code):
    sub_id = get_token(code)
    subscription = db('SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.id = '+str(sub_id),'select')
    if subscription['Status'] == 0:
        return redirect("/bills/quotation/"+code)
    profile = db('SELECT * FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))
    prof = {}
    amount = subscription['Amount']
    monthly = db('SELECT service.Monthly FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']))['Monthly']
    prof['id'] = sub_id
    prof['Name'] = profile['Name']
    prof['Currency'] = profile['Currency']
    prof['Amount'] = xrate(amount)
    prof['Total'] = xrate(1.038*float(amount))
    prof['Fees'] = xrate(0.038*float(amount))
    prof['Monthly'] = xrate(monthly)
    prof['Business'] = db('SELECT business.Name FROM '+dbname+'.business WHERE business.id = '+str(subscription['business_id']))['Name']
    prof['Service'] = db('SELECT service.Title FROM '+dbname+'.service WHERE service.id = '+str(subscription['service_id']))['Title']
    return render_template('emails/reciept.html', data=prof)
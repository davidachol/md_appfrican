from flask import Blueprint, request,session, redirect
from functions import db,get_token,set_token,dbname,servdb, login_required, mp
from flask import render_template_string, Markup, render_template, jsonify
from functools import wraps
import uuid
import mysql.connector
import json, requests

with open('plugins/vps/config.json') as config_file:
    config = json.load(config_file)

vps_host = config['database']['host']
vps_user = config['database']['user']
vps_passwd = config['database']['password']
vps_database = config['database']['database']

db_config = {'host':vps_host,'user':vps_user,'password':vps_passwd,'database':vps_database}

__plugin_name__ = "basic_vps"
__version__ = "1.1.0"
__author__ = "davidmarko"
prefix = '/basic_vps'

def subscription(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        sub_id = request.args.get("sub_id","")
        if sub_id != '':
            sub_id = get_token(sub_id)
            sub = db('SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.id = '+str(sub_id),'select')
            service = db('SELECT * FROM '+dbname+'.service WHERE service.id = '+str(sub['service_id']),'select')
            status = sub['Status']
            token = sub['Token']
            user_id = sub['user_id']
            if get_token(session['user_id']) != user_id:
                sub_check = db('SELECT invites.user_id, invites.sub_user FROM '+dbname+'.invites WHERE invites.sub_id = '+str(sub_id))
                if sub_check:
                    if user_id == sub_check['sub_user']:
                        pass
                    else:
                        return redirect('/auth/login')
                else:
                    return redirect('/auth/login')
            if service['Kind'] == 'Free':
                if token == '':
                    return redirect('/'+__plugin_name__+'/setup?sub_id='+set_token(sub_id))
                else:
                    session[__plugin_name__] = token
                    return f(*args, **kwargs)
            else:
                if status == 0:
                    return redirect('/business/view/'+str(sub['business_id']))
                elif status == 1:
                    if token == '':
                        return redirect('/'+service['config_file']+'/setup?sub_id='+set_token(sub_id))
                    else:
                        session[__plugin_name__] = token
                        return f(*args, **kwargs)
                elif status == 2:
                    return redirect('/bills/renew?sub_id='+set_token(sub_id))
                elif status == 3:
                    return f(*args, **kwargs)
        if __plugin_name__ in session:
            token = session[__plugin_name__]
            sub = db('SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.Token = "'+token+'"','select')
            if sub['Status'] == 0:
                return redirect("/business/view/"+str(set_token(sub['business_id'])))
            elif sub['Status'] == 1:
                return f(*args, **kwargs)
            elif sub['Status'] == 2:
                return redirect('/bills/renew?sub_id='+set_token(sub_id))
            elif sub['Status'] == 3:
                return f(*args, **kwargs)
    return decorated_function

basic_vps = Blueprint('basic_vps', 'basic_vps', template_folder='templates')

api_key = "k0DWw1DhEycT8LowHIHmTWS2Jv1wul8FLMrLb4gqhpRfQay6IwBlsUtX6cor848R7iKElxOurvIdkGVBrbhy2EErXrlUYbc"
vps_url = "https://www.vpsag.com/api/v1/"
headers = {
    'X_API_KEY': api_key,
    'X_API_USER': 'davidmarko'
}

@basic_vps.route('/')
@subscription
@login_required
def vps_home():
    token = session[__plugin_name__]
    sql = 'SELECT * FROM '+vps_database+'.vps_table WHERE vps_table.Token = "'+token+'";'
    vps = servdb(db_config,sql,'select')
    vps_id = vps['vps_id']
    url = vps_url + 'vps/'+str(vps_id)
    r = requests.get(url, headers=headers)
    response = json.loads(r.content)['result']
    print(response)
    if 'being installed' in response:
        return redirect('/'+__plugin_name__+'/loading')
    else:
        vnc_console = requests.get(vps_url+'vps/'+str(vps_id)+'/vnc', headers=headers).json()
        cpu_img = requests.get(vps_url+"vps/"+str(vps_id)+"/graph/hour", headers=headers).json()['result']['cpu_img']
        home = render_template("vps_home.html", response=response, vps=vps, vnc_console=vnc_console, cpu_img=cpu_img)
        return render_template('dashboard/plugin.html',serv=Markup(home))

@basic_vps.route('/loading')
def loading():
    sub_id = request.args.get("sub_id","")
    setup = render_template("loading.html")
    return render_template('dashboard/plugin.html',serv=Markup(setup))


@basic_vps.route('/setup', methods=['GET','POST'])
@login_required
def vps_setup():
    sub_id = request.args.get("sub_id","")
    if request.method == 'POST':
        token = "APPF-"+str(uuid.uuid1().int)[:12]
        ret = db('UPDATE '+dbname+'.subscriptions SET subscriptions.Token = "'+token+'" WHERE subscriptions.id = '+str(get_token(sub_id)),'update')
        url = vps_url + 'order'
        data = {
            'package': 6,
            'hostname': 'appfrican.co',
            'os': int(request.form['os']),
            'billing_term': 1
        }
        r = requests.post(url,data=data,headers=headers)
        if 'enough funds' in str(r.content):
            mp.track(session['user_id'],'Basic VPS Low Balance')
            return jsonify({'status':'error','message':'There was an internal error and will be resolved shortly'})
        response = json.loads(r.content)['result']
        print(response)
        sql = "INSERT INTO `vps_table` (`Token`, `Name`, `OS`, `vps_id`, `order_id`) VALUES ('"+token+"', 'appfrican.co', '"+request.form['os']+"', "+str(response['vps_id'])+", "+str(response['order_id'])+");"
        ret = servdb(db_config,sql,'insert')
        if ret:
            return jsonify({'status':'success'})
    else:
        url = vps_url + 'os/6'
        r = requests.get(url,headers=headers)
        os = json.loads(r.content)['result']
        setup = render_template("setup.html",os=os, sub_id=sub_id)
        return render_template('dashboard/plugin.html',serv=Markup(setup))


@basic_vps.route('/actions/<string:act>')
def vps_actions(act):
    if act == 'reboot':
        pass
    elif act == 'reinstall':
        pass
    return redirect('/'+__plugin_name__)


def register():
    return { 
        "bep": dict(blueprint=basic_vps, prefix=prefix)
    }


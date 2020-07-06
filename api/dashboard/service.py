from flask import Blueprint, jsonify, request, session, flash, redirect, render_template
from . import *
import base64

service = Blueprint('service','service', url_prefix='/service')

@service.route("/")
@login_required
def service_page():
    categories = db('SELECT DISTINCT service.Category FROM '+dbname+'.service WHERE 1 GROUP BY service.Category','many')
    services = db('SELECT * FROM '+dbname+'.service WHERE 1 ORDER BY service.id DESC LIMIT 0,8','many')
    return render_template('dashboard/service.html', categories=categories, services=services, page='')


@service.route("/category/<string:category>",methods=['GET','POST'])
@login_required
def s_category(category):
    categories = db('SELECT DISTINCT service.Category FROM '+dbname+'.service WHERE 1 GROUP BY service.Category','many')
    services = db('SELECT * FROM '+dbname+'.service WHERE service.Category = "'+category+'" ORDER BY service.id DESC','many')
    return render_template('dashboard/service.html', category=category, page='category', services=services,categories=categories)


@service.route("/overview/<string:id>", methods=['GET','POST'])
@login_required
def overview(id):
    service_id = get_token(id)
    servicez = db('SELECT * FROM '+dbname+'.service WHERE service.id = '+str(service_id),'select')
    profile = {}
    user = db('SELECT * FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))
    profile['email'] = user['Email']
    profile['txref'] = 'APP-'+str(uuid.uuid1().int)[:24]
    profile['business_id'] = session['select_biz']['id']
    profile['service_id'] = service_id
    profile['currency'] = user['Currency'].replace(" ","")
    servicez['Featured_Image'] = str(base64.b64encode(servicez['Featured_Image']).decode("utf-8"))
    return render_template('dashboard/service.html', page='overview',servicez=servicez, profile=profile)


@service.route("/rating",methods=['GET','POST'])
@login_required
def rating():
    return render_template('dashboard/service.html')

@service.route("/search/<string:code>",methods=['GET','POST'])
@login_required
def search(code):
    sql = "SELECT service.Title, service.id FROM "+dbname+".service WHERE service.Title LIKE '%"+code+"%';"
    ret = db(sql,'many')
    return jsonify(ret)
from flask import Flask, Blueprint, render_template, request, session
from flask_cors import CORS
from api.auth.auth_bp import auth_bp
from api.dashboard.home import home
from api.dashboard.business import business
from api.dashboard.service import service
from api.dashboard.bills import bills
from api.dashboard.alert import alert
from api.dashboard.profile import profile
from functions import mp, db, dbname, dbhost, dbpass, dbuser
from functions import set_token, get_token, xrate
from flask_pluginkit import PluginManager
import mysql.connector, base64, uuid

app = Flask(__name__)

CORS(app)
pm = PluginManager(app)

app.register_blueprint(auth_bp)
app.register_blueprint(home)
app.register_blueprint(business)
app.register_blueprint(service)
app.register_blueprint(bills)
app.register_blueprint(alert)
app.register_blueprint(profile)

app.secret_key = b'@!Another'
app.jinja_env.globals.update(session=session)
app.jinja_env.globals.update(set_token=set_token)
app.jinja_env.globals.update(get_token=get_token)
app.jinja_env.globals.update(xrate=xrate)
app.jinja_env.globals.update(float=float)
app.jinja_env.globals.update(str=str)
app.jinja_env.globals.update(base64=base64)

@app.route('/')
def hello():
   return render_template('frontpage/index.html')

@app.before_request
def before_request_func():
    if 'ref_code' in session:
        page = request.url
        ref_code = session['ref_code']
        ip = request.remote_addr
        user_agent = request.user_agent
        unique_id = session['unique_id']
        sql = "INSERT INTO `affiliate`(`id`, `Page`,`unique_id`, `Ref_code`, `IP`, `User_Agent`, `Date`) VALUES (NULL,'"+page+"','"+unique_id+"','"+ref_code+"','"+ip+"','"+user_agent+"',CURRENT_TIMESTAMP() );"
        db(sql,'insert')
    ref_code = request.args.get("ref_code","")
    if ref_code != "":
        session['ref_code'] = ref_code
        unique_id = str(uuid.uuid1().int)[:16]
        session['unique_id'] = unique_id

@app.route("/services")
def service_page():
    categories = db('SELECT DISTINCT service.Category FROM '+dbname+'.service WHERE 1 GROUP BY service.Category','many')
    services = db('SELECT * FROM '+dbname+'.service WHERE 1 ORDER BY service.id DESC LIMIT 0,10','many')
    return render_template('frontpage/services.html', categories=categories, services=services, page='')


@app.route("/services/category/<string:category>",methods=['GET','POST'])
def s_category(category):
    categories = db('SELECT DISTINCT service.Category FROM '+dbname+'.service WHERE 1 GROUP BY service.Category','many')
    services = db('SELECT * FROM '+dbname+'.service WHERE service.Category = "'+category+'" ORDER BY service.id DESC','many')
    return render_template('frontpage/services.html', category=category, page='category', services=services,categories=categories)

@app.route('/services/view/<string:code>')
def view_service(code):
   service_id = get_token(code)
   servicez = db('SELECT * FROM '+dbname+'.service WHERE service.id = '+str(service_id),'select')
   servicez['Featured_Image'] = str(base64.b64encode(servicez['Featured_Image']).decode("utf-8"))
   return render_template('frontpage/services.html', page='view',servicez=servicez)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        email = request.form['email']
        message = request.form['message']
        mp.track(email,'Message',{
            'Email': email,
            'Message': message
        })
    return render_template('frontpage/contact.html')

@app.route('/privacy', methods=['GET', 'POST'])
def privacy():
   return render_template('frontpage/privacy.html')

@app.route('/terms', methods=['GET', 'POST'])
def terms():
   return render_template('frontpage/privacy.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('400.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True)

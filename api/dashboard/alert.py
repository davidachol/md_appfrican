from flask import Blueprint, jsonify, request, session, flash, redirect, render_template
from . import *
from datetime import datetime

alert = Blueprint('alert','alert', url_prefix='/alert')

@alert.route('/', methods=['GET','POST'])
@login_required
def main_alert():
    row = db('SELECT alert.id, alert.Date, business.Name, service.Title, alert.Kind, alert.Rating, alert.Description, alert.Link, alert.Status FROM '+dbname+'.alert LEFT JOIN '+dbname+'.service ON service.id = alert.service_id LEFT JOIN '+dbname+'.business ON business.id = alert.business_id WHERE alert.user_id = '+str(get_token(session['user_id']))+' LIMIT 0,10','many')
    return render_template('dashboard/alert.html', row=row, page='')

@alert.route('/view/<string:code>', methods=['GET','POST'])
@login_required
def view_alert(code):
    alert_id = get_token(code)
    link = db('SELECT alert.Link FROM '+dbname+'.alert WHERE alert.id = '+str(alert_id),'select')['Link']
    db('UPDATE '+dbname+'.alert SET alert.Status = 1 WHERE alert.id = '+str(alert_id),'update')
    return redirect(link)


from flask import Blueprint, jsonify, request, session, flash, redirect, render_template
from . import *

profile = Blueprint('profile','profile', url_prefix='/profile')

@profile.route("/", methods=['GET','POST'])
@login_required
def profile_page():
    currencies = db('SELECT xrate.ToCurrency FROM '+dbname+'.xrate WHERE 1','many')
    prof = db('SELECT * FROM '+dbname+'.users WHERE users.id ='+str(get_token(session['user_id'])),'select')
    return render_template('dashboard/profile.html', page='', prof=prof, currencies=currencies)

@profile.route("/change_password", methods=['GET','POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form['current']
        new_password = request.form['new']
        user_id = get_token(session['user_id'])
        db_password = db('SELECT users.Password FROM '+dbname+'.users WHERE users.id = '+str(user_id),'select')['Password']
        if current == db_password:
            mp.track(session['user_id'], 'Change Password')
            db('UPDATE '+dbname+'.users SET users.Password = "'+new_password+'" WHERE users.id = '+str(user_id),'update')
            return jsonify({'status':'success'})
        else:
            return jsonify({'status':'error'})
    return render_template('dashboard/profile.html', page='')

@profile.route("/change_currency", methods=['GET','POST'])
@login_required
def change_currency():
    if request.method == 'POST':
        currency = request.form['currency']
        user_id = session['user_id']
        ret = db('UPDATE '+dbname+'.users SET users.Currency = "'+currency+'" WHERE users.id = '+str(get_token(user_id)),'update')
        if ret:
            return jsonify({'status':'success'})
        else:
            return jsonify({'status':'error'})
    return render_template('dashboard/profile.html', page='')

@profile.route("/request_data", methods=['GET','POST'])
@login_required
def request_data():
    mp.track(session['user_id'],'Data Request')
    return jsonify({'status':'success'})
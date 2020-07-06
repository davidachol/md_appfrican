from flask import Blueprint, jsonify, request, session, flash, redirect, render_template
from mixpanel import Mixpanel
from . import *

auth_bp = Blueprint('auth_bp','auth_bp', url_prefix='/auth')

@auth_bp.route('/login', methods=['POST','GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        check = db('SELECT users.id, users.Name, users.Email, users.Country, users.Currency FROM '+dbname+'.users WHERE users.Email = "'+str(email)+'" AND users.Password = "'+str(password)+'";')
        if check:
            session['user_id'] = set_token(check['id'])
            session['Email'] = check['Email']
            session['Name'] = check['Name']
            session['Country'] = check['Country']
            session['Currency'] = check['Currency']
            mp.track(session['user_id'],'Logged In')
            return jsonify({'status':'success', 'user_id':session['user_id']})
        else:
            return jsonify({'status':'error','message':'The username and password combination is incorrect'})
    else:
        if "user_id" in session:
            return redirect('/dashboard')
        return render_template('frontpage/login.html')

@auth_bp.route('/signup', methods=['POST','GET'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        country = request.form['country']
        gender = request.form['gender']
        currency = request.form['currency']
        token = str(uuid.uuid1().int)[:24]
        affiliate_code = str(uuid.uuid1().int)[:10]
        ref_code = ''
        if 'ref_code' in session:
            ref_code = session['ref_code']
            session.clear()
        check = db('SELECT * FROM '+dbname+'.users WHERE users.Email = "'+email+'"','select')
        if check:
            return jsonify({'status':'error','message':'Email Already Exists'})
        else:
            sql = f"INSERT INTO `users` (`id`, `Name`, `Email`, `Password`, `Token`, users.Currency, `Country`, `Date`, `Status`,`Ref`, `Affiliate_code`) VALUES (NULL, '{name}', '{email}', '{password}', '{token}', '{currency}' ,'{country}', current_timestamp(), '0','{ref_code}','{affiliate_code}');"
            last_row = db(sql,'insert')
            session['user_id'] = set_token(last_row)
            prof = {}
            prof['Name'] = name
            prof['verification_code'] = token
            send_mail('Welcome to Appfican', email, prof, email_template='welcome')
            session['Email'] = email
            session['Name'] = name
            session['Country'] = country
            mp.people_set(session['user_id'], {
                '$name': name,
                '$email': email,
                'token': token,
                '$country': country,
                '$currency': currency,
                '$gender': gender
            })
            return jsonify({'status':'success','user_id':session['user_id']})
    else:
        countries = db('SELECT * FROM '+dbname+'.country WHERE 1','many')
        currencies = db('SELECT * FROM '+dbname+'.xrate WHERE 1','many')
        return render_template('frontpage/signup.html', countries=countries, currencies=currencies)

@auth_bp.route('/resend_email', methods=['POST','GET'])
def resend_email():
    if 'user_id' not in session:
        return redirect('/auth/login')
    user = db('SELECT * FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))
    if request.method == 'POST': 
        if user['Status'] == 1:
            return jsonify({'status':'error','message':'The user has already been registered and verified'})
        elif user['Status'] == 0:
            prof = {}
            prof['Name'] = user['Name']
            prof['verification_code'] = user['Token']
            send_mail('Verify Email Address - Appfrican', user['Email'], prof, email_template='welcome')
            return jsonify({'status':'success','message':'The email has been sent, please check your mail and follow the link'})
    else:
        return render_template('frontpage/verify_account.html', email=user['Email'])

@auth_bp.route('/reset_password', methods=['POST','GET'])
def reset_password():
    code = request.args.get("code","")
    if request.method == 'POST':
        if code == "":
            email = request.form['email']
            check = db('SELECT * FROM '+dbname+'.users WHERE users.Email = "'+str(email)+'";')
            if check:
                token = str(uuid.uuid1().int)[:24]
                db('UPDATE '+dbname+'.users SET users.Token = "'+token+'" WHERE users.Email = "'+str(email)+'";','update')
                prof = {}
                prof['Email'] = email
                prof['Token'] = token
                send_mail("Reset Password",email,prof,'reset_pass')
                return jsonify({'status':'success'})
            else:
                return jsonify({'status':'error','message':'Email does not exists'})
        else:
            check = db('SELECT * FROM '+dbname+'.users WHERE users.Token = "'+code+'";')
            if check:
                password = request.form['password']
                db('UPDATE '+dbname+'.users SET users.Status = 1, users.Password = "'+password+'", users.Token = "" WHERE users.Token = '+str(code),'update')
                return jsonify({'status':'success'})
            else:
                return jsonify({'status':'error'})
    else:
        if code != '':
            check = db('SELECT * FROM '+dbname+'.users WHERE users.Token = "'+code+'";')
            if check:
                email = check['Email']
                return render_template('frontpage/reset_password.html',email=email, code=code)
            else:
                return render_template('frontpage/reset_password.html', error="Invalid Code")
        else:
            return render_template('frontpage/login.html')


@auth_bp.route('/email_verify/<string:code>', methods=['POST','GET'])
def verify_email(code):
    user = db('SELECT users.id FROM '+dbname+'.users WHERE users.Token = '+str(code))
    if user:
        db('UPDATE '+dbname+'.users SET users.Status = 1 WHERE users.id = '+str(user['id']),'update')
        session['user_id'] = set_token(user['id'])
        mp.track(session['user_id'],'Verified Email')
        return redirect('/dashboard')
    else:
        return redirect("/auth/login")

@auth_bp.route('/logout', methods=['POST','GET'])
@login_required
def logout():
    mp.track(session['user_id'],'Logged out')
    session.clear()
    return redirect('/auth/login')


#subuser verify, then create password
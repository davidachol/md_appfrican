from flask import Blueprint, jsonify, request, session, flash, redirect, render_template
from . import *

business = Blueprint('business','business', url_prefix='/business')

@business.route("/")
@login_required
def business_page():
    return render_template('dashboard/business.html')

@business.route("/add", methods=['POST','GET'])
def add():
    if 'user_id' in session:
        if request.method == 'POST':
            name = request.form['name']
            ## check if name exists
            check = db('SELECT * FROM '+dbname+'.business WHERE business.Name = "'+name+'"','select')
            if check:
                return jsonify({'status':'error','message':'Name Exists'})
            description = request.form['description']
            website = ''
            phone = request.form['phone']
            location = request.form['location']
            sector = request.form['sector']
            user_id = get_token(session['user_id'])
            sql = "INSERT INTO `business` \
                    (`id`, `Name`, `Website`, `Phone`, `Location`, `Description`, `Sector`, `Comment`, `Date`, `user_id`, `Status`) \
                        VALUES \
                (NULL, '"+name+"', '"+website+"', '"+phone+"', '"+location+"', '"+description+"', '"+sector+"', '', current_timestamp(), '"+str(user_id)+"', '1');"
            business_id = db(sql,'insert')
            mp.track(session['user_id'], 'Added Business',{
                'Name': name,
                '$sector': sector,
                'Description': description
            })
            return jsonify({'status':'success','business_id':set_token(business_id)})
        else:
            sectors = db('SELECT * FROM '+dbname+'.business_sectors','many')
            return render_template('dashboard/business.html', page='add', sectors=sectors)
    else:
        return redirect('/auth/login')

@business.route("/view/<string:business_id>", methods=['POST','GET'])
@login_required
def view(business_id):
    business_id = get_token(business_id)
    session['select_biz'] = db('SELECT business.id, business.Name FROM '+dbname+'.business WHERE business.id = '+str(business_id))
    check_subuser = db('SELECT * FROM '+dbname+'.business WHERE business.user_id = '+str(get_token(session['user_id']))+' AND business.id = '+str(business_id))
    if check_subuser:
        profile = db("SELECT `id`, `Name`, `Website`, `Phone`, `Location`, `Description`, `logo`, `Sector`, `Comment`, `Date`, business.user_id FROM `business` WHERE `id` = "+str(business_id),'select')
        services = db("SELECT subscriptions.id, subscriptions.service_id, service.Title, service.Subtitle, service.Kind, service.Category, service.config_file, subscriptions.Status FROM `subscriptions` LEFT JOIN "+dbname+".service ON service.id = subscriptions.service_id WHERE subscriptions.user_id = "+str(get_token(session['user_id']))+" AND subscriptions.business_id = "+str(business_id),'many')
        billing = db("SELECT subscriptions.id, business.Name, service.Title, service.Category, `txref`,`Duration`,subscriptions.Amount,`Next_billing_date`,`Total_paid`,subscriptions.Date,subscriptions.Status FROM `subscriptions` LEFT JOIN "+dbname+".business ON business.id = subscriptions.business_id LEFT JOIN "+dbname+".service ON service.id = subscriptions.service_id WHERE `business_id` = "+str(business_id)+" AND subscriptions.user_id = "+str(get_token(session['user_id'])),'many')
        business_admin = db('SELECT users.Email, users.Name FROM '+dbname+'.users WHERE users.id = '+str(profile['user_id']))
        others = db('SELECT users.Email, users.Name, invites.Role, invites.Comment FROM '+dbname+'.invites LEFT JOIN '+dbname+'.users ON users.id = invites.sub_user WHERE invites.business_id = '+str(business_id),'many')
        return render_template('dashboard/business.html', page='view',business_admin=business_admin, others=others, profile=profile, services=services, billing=billing)
    else:
        profile = db("SELECT business.id,business.Name,business.Website,business.Phone,business.Location,business.Description,business.Sector,business.user_id FROM `business` LEFT JOIN "+dbname+".invites ON business.id = invites.business_id WHERE invites.sub_user = "+str(get_token(session['user_id']))+" AND invites.business_id = "+str(business_id),'select')
        if profile:
            services = db("SELECT subscriptions.id, subscriptions.service_id, service.Title, service.Subtitle, service.Kind, service.Category, service.config_file, subscriptions.Status FROM "+dbname+".invites LEFT JOIN "".subscriptions ON subscriptions.id = invites.sub_id LEFT JOIN "+dbname+".service ON service.id = subscriptions.service_id WHERE invites.sub_user = "+str(get_token(session['user_id']))+" AND invites.business_id = "+str(business_id),'many')
            business_admin = db('SELECT users.Email, users.Name FROM '+dbname+'.users WHERE users.id = '+str(profile['user_id']))
            others = db('SELECT users.Email, users.Name, invites.Role, invites.Comment FROM '+dbname+'.invites LEFT JOIN '+dbname+'.users ON users.id = invites.sub_user WHERE invites.business_id = '+str(business_id),'many')
            return render_template('dashboard/business.html', page='sub_view', profile=profile, business_admin=business_admin, services=services, others=others)
        else:
            return redirect('/dashboard')

@business.route("/edit", methods=['POST','GET'])
@login_required
def edit():
    if request.method == 'POST':
        name = request.form['name']
        website = ""
        description = request.form['description']
        location = request.form['location']
        phone = request.form['phone']
        sql = "UPDATE "+dbname+".business SET business.Name = '"+name+"', business.Website = '"+website+"', business.Description = '"+description+"', business.Location = '"+location+"', business.Phone = '"+phone+"' WHERE business.id = "+ str(session['select_biz']['id'])
        if db(sql,'update') == True:
            mp.track(session['user_id'], 'Edit Business', {
                'business_id': set_token(session['select_biz']['id']),
                'Name': name,
                'Description': description
            })
            return redirect("/business/view/"+set_token(session['select_biz']['id']))
        else:
            return redirect(request.url)

@business.route("/invite/<string:page>", methods=['POST','GET'])
@login_required
def invite(page):
    if page == 'add':
        if request.method == 'POST':
            email = request.form['email']
            role = request.form['role']
            comment = request.form['comment']
            business_id = request.form['business_id']
            service = request.form['service']
            check = db('SELECT * FROM '+dbname+'.subscriptions WHERE subscriptions.id = '+str(get_token(service))+' \
            AND subscriptions.business_id = '+str(get_token(business_id))+' AND subscriptions.user_id = '+str(get_token(session['user_id'])))
            if check:
                check_email = db('SELECT * FROM '+dbname+'.users WHERE users.Email = "'+email+'"')
                if check_email:
                    sub_user = check_email['id']
                    sql = "INSERT INTO `invites`(`id`, `user_id`, `sub_id`, `Role`, `business_id`, `sub_user`, `Date`, `Comment`, `Status`) VALUES (NULL,"+str(get_token(session['user_id']))+","+str(get_token(service))+",'"+role+"',"+str(get_token(business_id))+","+str(sub_user)+",CURRENT_TIMESTAMP(),'"+comment+"',1)"
                    db(sql,'insert')
                    alert(get_token(session['user_id']),get_token(service),get_token(business_id),'invite','/business/view/'+business_id)
                    alert(sub_user,get_token(service),get_token(business_id),'invite','/business/view/'+business_id)
                    details = {}
                    details['business_id'] = get_token(business_id)
                    details['business'] = db("SELECT business.Name FROM "+dbname+".business WHERE business.id = "+str(get_token(business_id)),'select')['Name']
                    details['from_email'] = db('SELECT users.Email FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))['Email']
                    send_mail('Invite for '+details['business'],email,details,email_template='invite')
                    return jsonify({'status':'success'})
                else:
                    return jsonify({'status':'error', 'message': 'The user isnt registered on the platform. Invites can only be sent to registered users.'})
            else:
                return jsonify({'status':'error'})
    elif page == 'suspend':
        email = request.args.get("email","")
        if request.method == 'POST':
            pass
        else:
            pass
    elif page == 'service':
        email = request.args.get("email","")
        if request.method == 'POST':
            #insert another invite, 
            pass
        else:
            pass
    else:
        pass

@business.route("/change_selected/<string:biz_id>", methods=['POST','GET'])
@login_required
def change_selected(biz_id):
    #change select_biz item in the sessions and redirect to business view
    return render_template('dashboard/business.html')

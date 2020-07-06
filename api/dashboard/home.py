from flask import Blueprint, jsonify, request, session, flash, redirect, render_template
from . import *
import pygal
from pygal.style import Style

home = Blueprint('home','home', url_prefix='/dashboard')

@home.route('/line')
@login_required
def line():
    custom_style = Style(background='transparent')
    line = pygal.Line(x_label_rotation=20,style=custom_style,legend_at_bottom=True,legend_box_size=18)
    #transaction = db("SELECT `Amount`, `Date` FROM `affiliate_transactions` WHERE `Status` = 1 AND `user_id` = "+str(get_token(session['user_id'])),'many')
    transaction = db("SELECT subscriptions.Amount FROM "+dbname+".subscriptions WHERE subscriptions.user_id = "+str(get_token(session['user_id'])),'many')
    dates = []
    for each in transaction:
        dates.append(each['Amount'])
    #line.x_labels = map(str, range(1,23000))
    line.title = ""
    line.add("Subscriptions",dates)
    line = line.render_response()
    return line


@home.route('/pie')
@login_required
def pie():
    custom_style = Style(background='transparent')
    pie_chart = pygal.Pie(style=custom_style,legend_at_bottom=True)
    pie_chart.title = 'Business Sector'
    sectors = db('SELECT DISTINCT business.Sector, COUNT(*) as "Total" FROM '+dbname+'.business WHERE business.user_id = '+str(get_token(session['user_id']))+' GROUP BY business.Sector','many')
    for sect in sectors:
        pie_chart.add(sect['Sector'],sect['Total'])
    pie_chart = pie_chart.render_response()
    return pie_chart

@home.route("/")
@login_required
def mainpage():
    sql = "SELECT subscriptions.id,business.Name, service.Title, `Next_billing_date`,DATEDIFF(`Next_billing_date`,CURDATE()) as 'Days' FROM "+dbname+".subscriptions LEFT JOIN "+dbname+".service ON service.id = subscriptions.service_id LEFT JOIN "+dbname+".business ON business.id = subscriptions.business_id WHERE DATEDIFF(`Next_billing_date`,CURDATE()) < 8 AND subscriptions.Status = 1 AND subscriptions.user_id = "+str(get_token(session['user_id']))
    expiring = db(sql,'many')
    sql = "SELECT subscriptions.id, service.Title, service.Subtitle, service.Comment, service.icon, service.config_file, subscriptions.Status, service.Category FROM "+dbname+".subscriptions LEFT JOIN "+dbname+".service ON service.id = subscriptions.service_id WHERE subscriptions.user_id = "+str(get_token(session['user_id']))+" AND subscriptions.Status = 1 ORDER BY subscriptions.id DESC LIMIT 0,2"
    services = db(sql,'many')
    alertz = db('SELECT alert.id, alert.Date, business.Name, service.Title, alert.Kind, alert.Rating, alert.Description, alert.Link, alert.Status FROM '+dbname+'.alert LEFT JOIN '+dbname+'.service ON service.id = alert.service_id LEFT JOIN '+dbname+'.business ON business.id = alert.business_id WHERE alert.user_id = '+str(get_token(session['user_id']))+' ORDER BY alert.id DESC LIMIT 0,5','many') 
    withdrawn = db('SELECT SUM(affiliate_transactions.Amount) as "Total" FROM '+dbname+'.affiliate_transactions WHERE affiliate_transactions.Status = 1 AND affiliate_transactions.user_id = '+str(get_token(session['user_id'])))['Total']
    withdrawn = xrate(withdrawn)
    earned = db('SELECT SUM(affiliate_transactions.Amount) as "Total" FROM '+dbname+'.affiliate_transactions WHERE affiliate_transactions.user_id = '+str(get_token(session['user_id'])))['Total']
    earned = xrate(earned)
    left = db('SELECT SUM(affiliate_transactions.Amount) as "Total" FROM '+dbname+'.affiliate_transactions WHERE affiliate_transactions.Status = 0 AND affiliate_transactions.user_id = '+str(get_token(session['user_id'])))['Total']
    left = xrate(left)
    profile = db('SELECT * FROM '+dbname+'.users WHERE users.id = '+str(get_token(session['user_id'])))
    stats = {}
    stats['total_biz'] = db('SELECT COUNT(*) as "Total" FROM '+dbname+'.business WHERE business.user_id = '+str(get_token(session['user_id'])))['Total']
    stats['installed'] = db('SELECT COUNT(*) as "Total" FROM '+dbname+'.subscriptions WHERE subscriptions.Status = 1 AND subscriptions.user_id = '+str(get_token(session['user_id'])))['Total']
    stats['total_alert'] = db('SELECT COUNT(*) as "Total" FROM '+dbname+'.alert WHERE alert.Status = 0 AND alert.user_id = '+str(get_token(session['user_id'])))['Total']
    stats['pending'] = db('SELECT COUNT(*) as "Total" FROM '+dbname+'.subscriptions WHERE subscriptions.Status != 1 AND subscriptions.user_id = '+str(get_token(session['user_id'])))['Total']
    return render_template('dashboard/home.html',profile=profile, earned=earned,withdrawn=withdrawn,left=left, expiring=expiring, services=services,alertz=alertz, stats=stats)

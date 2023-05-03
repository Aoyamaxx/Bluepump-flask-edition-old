from flask import Flask, request, session, render_template, redirect, send_from_directory
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask import jsonify
import uuid
import json
import urllib.parse

# Configure app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_tracking.db'

# Configure flask session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database and database models
db = SQLAlchemy(app)

class SiteVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(36))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    referrer_url = db.Column(db.String(255))
    entry_time = db.Column(db.DateTime)
    exit_time = db.Column(db.DateTime)
    last_page = db.Column(db.String(255))

class DonatePopup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(36))
    action = db.Column(db.String(50))

    def __init__(self, visitor_id, action):
        self.visitor_id = visitor_id
        self.action = action

class PrivacyPolicy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(36), nullable=False)
    decision = db.Column(db.String(2), nullable=False)  # 'Y' for accept, 'N' for reject, 'NA' for no action recorded

    def __init__(self, visitor_id, decision):
        self.visitor_id = visitor_id
        self.decision = decision

with app.app_context():
    db.create_all()

# Function to log data: this function saves the time spent on the previous page in the database. Unit of time is seconds.
def generate_visitor_id():
    return str(uuid.uuid4())[:10]
    
def decode_url(url):
    return urllib.parse.unquote(url)

def log_site_visit(visitor_id):
    referrer = request.headers.get('Referer', None)
    site_visit = SiteVisit(
        visitor_id=visitor_id,
        entry_time=datetime.now(),
        ip_address=get_user_ip(),
        user_agent=request.user_agent.string,
        referrer_url=referrer)
    db.session.add(site_visit)
    db.session.commit()

def log_site_visit_once(visitor_id):
    if 'site_visit_logged' not in session or not session['site_visit_logged']:
        referrer = request.headers.get('Referer', None)
        site_visit = SiteVisit(
            visitor_id=visitor_id,
            entry_time=datetime.now(),
            ip_address=get_user_ip(),
            user_agent=request.user_agent.string,
            referrer_url=referrer)
        db.session.add(site_visit)
        db.session.commit()
        session['site_visit_logged'] = True

def get_user_ip():
    if 'X-Forwarded-For' in request.headers:
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    return request.remote_addr

def save_user_action(visitor_id, action):
    donate_popup = DonatePopup(visitor_id=visitor_id, action=action)
    db.session.add(donate_popup)
    db.session.commit()
    
def log_exit(last_page):
    site_visit = SiteVisit.query.filter_by(visitor_id=session.get('visitor_id')).order_by(SiteVisit.id.desc()).first()
    if site_visit:
        site_visit.exit_time = datetime.now()
        site_visit.last_page = last_page
        db.session.commit()
    
@app.route('/track_exit', methods=['POST'])
def track_exit_route():
    last_page = request.form.get('last_page')
    log_exit(last_page)
    return '', 204

@app.route('/get_visitor_id', methods=['GET'])
def get_visitor_id():
    visitor_id = str(uuid.uuid4())
    return jsonify(visitor_id=visitor_id)

@app.route('/privacy_banner')
def privacy_banner():
    return render_template('privacy_banner.html')

@app.route('/learn_more')
def learn_more():
    visitor_id = session.get("visitor_id", generate_visitor_id())
    log_site_visit_once(visitor_id)
    return render_template('learn_more.html')

@app.route('/log_privacy_decision', methods=['POST'])
def log_privacy_decision():
    visitor_id = request.form['visitor_id']
    decision = request.form['decision']
    privacy_policy_record = PrivacyPolicy(visitor_id, decision)
    db.session.add(privacy_policy_record)
    db.session.commit()
    return jsonify(success=True)

@app.route('/track_user_action', methods=['POST'])
def track_user_action():
    visitor_id = request.form.get('visitor_id')
    if not visitor_id:
        visitor_id = session.get('visitor_id')
    action = request.form.get('action')

    # Save the action to the database (you need to implement this function)
    save_user_action(visitor_id, action)

    return 'OK'

@app.route('/donate_popup')
def donate_popup():
    return render_template('donate_popup.html')

@app.route('/')
def index():
    visitor_id = request.args.get('uid')
    if not visitor_id:
        visitor_id = generate_visitor_id()
    session["visitor_id"] = visitor_id
    log_site_visit(visitor_id)
    log_site_visit_once(visitor_id)
    return render_template('index.html', visitor_id=visitor_id)

@app.route('/about')
def about():
    visitor_id = session.get("visitor_id", generate_visitor_id())
    log_site_visit_once(visitor_id)
    return render_template('about.html')

@app.route('/map')
def map():
    visitor_id = session.get("visitor_id", generate_visitor_id())
    log_site_visit_once(visitor_id)
    return render_template('map.html')

@app.route('/projects')
def projects():
    visitor_id = session.get("visitor_id", generate_visitor_id())
    log_site_visit_once(visitor_id)
    return render_template('projects.html')

@app.route('/donate')
def donate():
    visitor_id = session.get("visitor_id", generate_visitor_id())
    log_site_visit_once(visitor_id)
    return render_template('donate.html')

@app.route('/siaya')
def siaya():
    visitor_id = session.get("visitor_id", generate_visitor_id())
    log_site_visit_once(visitor_id)
    return render_template('siaya.html')


@app.route('/header')
def header():
    return render_template('header.html')

@app.route('/footer')
def footer():
    return render_template('footer.html')

if __name__ == '__main__':
    app.run()
from flask import Flask, request, session, render_template, redirect, send_from_directory
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask import jsonify
import uuid
import urllib.parse

# Configure app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_tracking.db'

# Configure flask session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./flask_session"
app.secret_key = "pipers"
Session(app)

# Set up database and database models
db = SQLAlchemy(app)

class SiteVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(36))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
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

class DonateClick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(36), nullable=False)
    header_clicks = db.Column(db.Integer, nullable=False, default=0)
    index_clicks = db.Column(db.Integer, nullable=False, default=0)

    def __init__(self, visitor_id):
        self.visitor_id = visitor_id
        self.header_clicks = 0
        self.index_clicks = 0

with app.app_context():
    db.create_all()

# Function to log data: this function saves the time spent on the previous page in the database. Unit of time is seconds.
def generate_visitor_id():
    return str(uuid.uuid4())[:10]

def decode_url(url):
    return urllib.parse.unquote(url)

def log_site_visit(visitor_id):
    site_visit = SiteVisit(
        visitor_id=visitor_id,
        entry_time=datetime.now(),
        ip_address=get_user_ip(),
        user_agent=request.user_agent.string,
    )
    db.session.add(site_visit)
    db.session.commit()

def log_site_visit_once(visitor_id):
    if 'site_visit_logged' not in session or not session['site_visit_logged']:
        site_visit = SiteVisit(
            visitor_id=visitor_id,
            entry_time=datetime.now(),
            ip_address=get_user_ip(),
            user_agent=request.user_agent.string,
        )
        db.session.add(site_visit)
        db.session.commit()
        session['site_visit_logged'] = True
        session.modified = True
    else:
        session.modified = False

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

def update_donate_clicks(visitor_id, button_type):
    donate_click = DonateClick.query.filter_by(visitor_id=visitor_id).first()
    if not donate_click:
        donate_click = DonateClick(visitor_id=visitor_id)
        db.session.add(donate_click)

    if button_type == 'header':
        donate_click.header_clicks += 1
    elif button_type == 'index':
        donate_click.index_clicks += 1

    db.session.commit()

@app.route('/track_donate_click', methods=['POST'])
def track_donate_click():
    visitor_id = request.form.get('visitor_id')
    button_type = request.form.get('button_type')
    update_donate_clicks(visitor_id, button_type)
    return 'OK'

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
    visitor_id = session.get("visitor_id")
    if not visitor_id:
        visitor_id = generate_visitor_id()
        session["visitor_id"] = visitor_id
    log_site_visit_once(visitor_id)
    return render_template('index.html', visitor_id=visitor_id)

@app.route('/about')
def about():
    visitor_id = session.get("visitor_id")
    if not visitor_id:
        visitor_id = generate_visitor_id()
        session["visitor_id"] = visitor_id
    log_site_visit_once(visitor_id)
    return render_template('about.html')

@app.route('/map')
def map():
    if 'visitor_id' not in session:
        session["visitor_id"] = generate_visitor_id()
    visitor_id = session["visitor_id"]
    log_site_visit_once(visitor_id)
    return render_template('map.html')

@app.route('/projects')
def projects():
    if 'visitor_id' not in session:
        session["visitor_id"] = generate_visitor_id()
    visitor_id = session["visitor_id"]
    log_site_visit_once(visitor_id)
    return render_template('projects.html')

@app.route('/donate')
def donate():
    if 'visitor_id' not in session:
        session["visitor_id"] = generate_visitor_id()
    visitor_id = session["visitor_id"]
    log_site_visit(visitor_id)
    return render_template('donate.html')

@app.route('/siaya')
def siaya():
    if 'visitor_id' not in session:
        session["visitor_id"] = generate_visitor_id()
    visitor_id = session["visitor_id"]
    log_site_visit_once(visitor_id)
    return render_template('siaya.html')

@app.route('/header')
def header():
    return render_template('header.html')

@app.route('/footer')
def footer():
    return render_template('footer.html')

@app.route('/gallery_mali')
def gallery_mali():
    country_images = [{'filename': 'mali/mali1.jpg'}, {'filename': 'mali/mali2.jpg'}, {'filename': 'mali/mali3.jpg'}, {'filename': 'mali/mali4.jpg'}, {'filename': 'mali/mali5.jpg'}, {'filename': 'mali/mali6.jpg'}, {'filename': 'mali/mali7.jpg'}, {'filename': 'mali/mali8.jpg'}, {'filename': 'mali/mali9.jpg'}, {'filename': 'mali/mali10.jpg'}, {'filename': 'mali/mali11.jpg'}, {'filename': 'mali/mali12.jpg'}, {'filename': 'mali/mali13.jpg'}, {'filename': 'mali/mali14.jpg'}, {'filename': 'mali/mali15.jpg'}, {'filename': 'mali/mali16.jpg'}, {'filename': 'mali/mali17.jpg'}, {'filename': 'mali/mali18.jpg'}, {'filename': 'mali/mali19.jpg'}, {'filename': 'mali/mali20.jpg'}, {'filename': 'mali/mali21.jpg'}, {'filename': 'mali/mali22.jpg'}, {'filename': 'mali/mali23.jpg'}, {'filename': 'mali/mali24.jpg'}, {'filename': 'mali/mali25.jpg'}, {'filename': 'mali/mali26.jpg'}, {'filename': 'mali/mali27.jpg'}, {'filename': 'mali/mali28.jpg'}, {'filename': 'mali/mali29.jpg'}, {'filename': 'mali/mali30.jpg'}, {'filename': 'mali/mali31.jpg'}, {'filename': 'mali/mali32.jpg'}, {'filename': 'mali/mali33.jpg'}, {'filename': 'mali/mali34.jpg'}, {'filename': 'mali/mali35.jpg'}, {'filename': 'mali/mali36.jpg'}, {'filename': 'mali/mali37.jpg'}, {'filename': 'mali/mali38.jpg'}, {'filename': 'mali/mali39.jpg'}, {'filename': 'mali/mali40.jpg'}, {'filename': 'mali/mali41.jpg'}, {'filename': 'mali/mali42.jpg'}, {'filename': 'mali/mali43.jpg'}, {'filename': 'mali/mali44.jpg'}]
    return render_template('gallery_mali.html', country_images=country_images)

@app.route('/gallery_kenya')
def gallery_kenya():
    country_images = [{'filename': 'kenya/kenya1.jpg'}, {'filename': 'kenya/kenya2.jpg'}, {'filename': 'kenya/kenya3.jpg'}, {'filename': 'kenya/kenya4.jpg'}, {'filename': 'kenya/kenya5.jpg'}, {'filename': 'kenya/kenya6.jpg'}, {'filename': 'kenya/kenya7.jpg'}]
    return render_template('gallery_kenya.html', country_images=country_images)

@app.route('/gallery_burkina')
def gallery_burkina():
    country_images = [{'filename': 'burkina/burkina1.jpg'}, {'filename': 'burkina/burkina2.jpg'}, {'filename': 'burkina/burkina3.jpg'}, {'filename': 'burkina/burkina4.jpg'}, {'filename': 'burkina/burkina5.jpg'}, {'filename': 'burkina/burkina6.jpg'}, {'filename': 'burkina/burkina7.jpg'}, {'filename': 'burkina/burkina8.jpg'}, {'filename': 'burkina/burkina9.jpg'}, {'filename': 'burkina/burkina10.jpg'}, {'filename': 'burkina/burkina11.jpg'}, {'filename': 'burkina/burkina12.jpg'}, {'filename': 'burkina/burkina13.jpg'}, {'filename': 'burkina/burkina14.jpg'}, {'filename': 'burkina/burkina15.jpg'}, {'filename': 'burkina/burkina16.jpg'}, {'filename': 'burkina/burkina17.jpg'}, {'filename': 'burkina/burkina18.jpg'}, {'filename': 'burkina/burkina19.jpg'}, {'filename': 'burkina/burkina20.jpg'}, {'filename': 'burkina/burkina21.jpg'}, {'filename': 'burkina/burkina22.jpg'}, {'filename': 'burkina/burkina23.jpg'}, {'filename': 'burkina/burkina24.jpg'}]
    return render_template('gallery_burkina.html', country_images=country_images)

if __name__ == '__main__':
    app.run()
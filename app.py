from flask import Flask, request, session, render_template, redirect
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session

# Configure app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_tracking.db'

# Configure flask session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database and database models
db = SQLAlchemy(app)

class PageView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(10))
    page = db.Column(db.String(255))
    time_spent = db.Column(db.Integer)
    start_time = db.Column(db.DateTime)

class Button(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(10))
    button_name = db.Column(db.String(50))
    click_count = db.Column(db.Integer)
    first_click_time = db.Column(db.DateTime)

class SiteVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(10))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(255))
    referrer_url = db.Column(db.String(255))
    entry_time = db.Column(db.DateTime)
    exit_time = db.Column(db.DateTime)
    last_page = db.Column(db.String(255))

with app.app_context():
    db.create_all()

# Function to log data: this function saves the time spent on the previous page in the database. Unit of time is seconds. 
def log_data():
    try:
        time_spent = (datetime.now() - session['start_time']).total_seconds()

        # First 3 seconds is the threshold to save the time spent in the database. It is to eliminate recording repetitive page requests/reloads. 
        if time_spent > 3:
            page_view = PageView(
                visitor_id=session.get('visitor_id'),
                page=session['previous_path'],
                time_spent=time_spent,
                start_time=session['start_time'])
            db.session.add(page_view)
            db.session.commit()
    except:
        pass

def log_exit():
    site_visit = SiteVisit.query.filter_by(visitor_id=session.get('visitor_id')).first()
    if site_visit:
        site_visit.exit_time = datetime.now()
        site_visit.last_page = session['previous_path']
        db.session.commit()
        
def get_user_ip():
    if 'X-Forwarded-For' in request.headers:
        return request.headers.getlist("X-Forwarded-For")[0].split(',')[0]
    return request.remote_addr

@app.after_request
def track_time(response):
    if 'start_time' not in session:
        session['start_time'] = datetime.now()
    log_data()
    session['start_time'] = datetime.now()
    session['previous_path'] = request.path
    return response

@app.route('/')
def index():
    visitor_id = request.args.get('uid')
    if visitor_id:
        session["visitor_id"] = visitor_id
        site_visit = SiteVisit(
            visitor_id=visitor_id,
            entry_time=datetime.now(),
            ip_address=get_user_ip(),
            user_agent=request.user_agent.string,
            referrer_url=request.referrer)
        db.session.add(site_visit)
        db.session.commit()
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/map')
def map():
    return render_template('map.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/donate')
def donate():
    return render_template('donate.html')

@app.route('/siaya')
def siaya():
    return render_template('siaya.html')

@app.route('/track_button_click/<string:button_name>')
def track_button_click(button_name):
    visitor_id = session.get('visitor_id')
    button = Button.query.filter_by(visitor_id=visitor_id, button_name=button_name).first()

    if not button:
        button = Button(visitor_id=visitor_id, button_name=button_name, click_count=1, first_click_time=datetime.now())
        db.session.add(button)
    else:
        button.click_count += 1

    db.session.commit()
    return '', 204

if __name__ == '__main__':
    app.run()
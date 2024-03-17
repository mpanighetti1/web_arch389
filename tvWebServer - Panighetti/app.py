# Import required libraries
from flask import Flask, render_template, redirect, url_for, session, flash, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegistrationForm, LoginForm
from collections import defaultdict
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from waitress import serve  # For Windows Server Multi-threading
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',  # Include timestamp
    datefmt='%Y-%m-%d %H:%M:%S'  # Set format for the timestamp
)
logger = logging.getLogger('MyAppLogger')
handler = RotatingFileHandler('myapp.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
# Set format for handler
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S'))
logger.addHandler(handler)

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ksadlhfgalkjhfdgbsadfslkjhsb'

# MongoDB connection setup
uri = "mongodb+srv://mpanighetti:c3inqtGr3E9n4fXG@webarch-tvserver.b1ncqok.mongodb.net/?retryWrites=true&w=majority"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'), tlsCAFile='cacert-2023-08-22.pem')

# Try to ping MongoDB to ensure connection
try:
    client.admin.command('ping')
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error("Failed to connect to MongoDB: %s", e)

# Connect to the desired MongoDB database and collections
db = client['WebArch-TVServer']
users = db.users  # Collection for user authentication
time_spent = db.time_spent  # Collection for tracking user time activity
active_sessions = db.active_sessions  # Collection for tracking active sessions

######################### Connection Pings and Session Validation ##############

@app.route('/validate_session', methods=['HEAD'])
def validate_session():
    # Check if the user session is active and return appropriate response
    if 'username' in session:
        return '', 200  # OK status, no content
    else:
        return '', 401  # Unauthorized, no content

@app.route('/ping', methods=['POST'])
def ping():
    username = request.json.get('username')
    if username:
        active_sessions.update_one({"username": username}, {"$set": {"last_ping": datetime.now()}})
        print("Ping received for user: ", username)
        return jsonify({"message": "Ping received"}), 200
    else:
        print("Username not provided")
        return jsonify({"message": "Username not provided"}), 400
    
def check_inactive_sessions():
    # Check and logout inactive user sessions
    inactive_threshold = datetime.now() - timedelta(minutes=2)
    inactive_users = active_sessions.find({"last_ping": {"$lt": inactive_threshold}})
    for user in inactive_users:
        print("Logging out inactive user: ", user['username'])
        logger.info("Logging out inactive user: %s", user['username'])
        logout(user['username'], norm_logout=False)
    
scheduler = BackgroundScheduler()
scheduler.add_job(check_inactive_sessions, 'interval', minutes=1)
scheduler.start()

############################# User Authentication Routes #######################

@app.route("/register", methods=['GET', 'POST'])
def register():
    # User registration route
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        users.insert_one({
            "username": form.username.data,
            "password": hashed_password
        })
        flash('Account created!', 'success')
        logger.info("New user registered: %s", form.username.data)
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    # User login route
    form = LoginForm()
    if form.validate_on_submit():
        user = users.find_one({"username": form.username.data})
        if user and check_password_hash(user['password'], form.password.data):
            session['username'] = form.username.data
            time_spent.insert_one({
                    "username": form.username.data,
                    "action": "login",
                    "timestamp": datetime.now(),
            })
            active_sessions.insert_one({
                "username": form.username.data,
                "login_time": datetime.now()
            })
            logger.info("Login successful for user: %s", form.username.data)
            return redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout', methods=['GET', 'POST'])
def logout(username=None, norm_logout=True):
    # User logout route
    if not username:
        username = session.get('username')
    if username:
        login_record = active_sessions.find_one({"username": username})
        if login_record:
            login_time = login_record['login_time']
            current_time = datetime.now()
            duration = (current_time - login_time).total_seconds()
            try:
                time_spent.insert_one({
                    "username": username,
                    "action": "logout",
                    "timestamp": current_time,
                    "session_duration": duration
                })
                active_sessions.delete_one({"username": username})
                logger.info("Logout successful for user: %s", username)
            except Exception as e:
                logger.error("Error during logout for user %s: %s", username, e)
        if (norm_logout):
            return redirect(url_for('login'))
    else:
        if (norm_logout):
            flash("No user logged in", "error")
            return redirect(url_for('login'))

########################### Admin UI Page Route #################################

def is_admin():
    # Check if the logged-in user is an administrator
    return 'username' in session and session['username'] == 'admin'

@app.route('/admin')
def admin():
    # Admin dashboard route
    if not is_admin():
        return redirect(url_for('index'))

    # Determine the default start and end dates based on the data
    earliest_record = time_spent.find_one(sort=[("timestamp", 1)])  # Get the earliest record
    latest_record = time_spent.find_one(sort=[("timestamp", -1)])   # Get the latest record

    # Format the earliest and latest timestamps, or default to current date
    default_start_date_str = earliest_record['timestamp'].strftime('%Y-%m-%d') if \
        earliest_record else \
            datetime.now().strftime('%Y-%m-%d')
    default_end_date_str = latest_record['timestamp'].strftime('%Y-%m-%d') if \
        latest_record else \
            (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    # Process query parameters or use default dates
    start_date_str = request.args.get('start_date', default_start_date_str)
    end_date_str = request.args.get('end_date', default_end_date_str)
    time_increment = request.args.get('increment', 'hourly')

    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    query = {
        "action": {"$in": ["login", "logout"]},
        "timestamp": {"$gte": start_date, "$lt": end_date}
    }
    all_records = list(time_spent.find(query).sort("timestamp", 1))

    # Prepare data structures for concurrent user calculation
    user_status = defaultdict(bool)
    concurrent_users = defaultdict(set)
    user_total_time = defaultdict(int)

    session_duration_records = time_spent.find({
        "action": "logout",
        "timestamp": {"$gte": start_date, "$lt": end_date}
    })

    for record in session_duration_records:
        username = record['username']
        duration = record.get('session_duration', 0)
        user_total_time[username] += duration

    user_time_data = [{'username': user, 'total_time': total_time / 60}
                      for user, total_time in sorted(user_total_time.items(), 
                                                     key=lambda item: item[1], reverse=True)]

    for record in all_records:
        timestamp = record['timestamp']
        action = record['action']
        username = record['username']

        if action == "login":
            user_status[username] = True
        elif action == "logout":
            user_status[username] = False

        if user_status[username]:
            if time_increment == 'hourly':
                formatted_time_point = timestamp.replace(minute=0, second=0, microsecond=0)
            else:
                formatted_time_point = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            concurrent_users[formatted_time_point].add(username)

    chart_data = [{'time': time.strftime("%Y-%m-%d %H:%M:%S"), 'count': len(users)} 
                  for time, users in sorted(concurrent_users.items())]

    return render_template('admin.html', 
                           chart_data=chart_data, 
                           user_time_data=user_time_data, 
                           start_date=start_date_str, 
                           end_date=end_date_str, 
                           increment=time_increment,
                           username='admin')

############################# Main Index Route ##################################

@app.route('/')
def index():
    # Main index route
    if 'username' in session:
        if session['username'] == 'admin':
            return render_template('chart_admin.html', username=session['username'])
        else:
            return render_template('chart.html', username=session['username'])
    else:
        return redirect(url_for('login'))

# Start the Flask application using waitress for Windows multi-threading
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=8000, threads=6)


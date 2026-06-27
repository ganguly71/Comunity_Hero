import os
import math
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import db, User, Issue, Comment, Vote, UpdateLog, SentMail
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from supabase import create_client, Client

def haversine_distance(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float('inf')
    R = 6371.0  # Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def geocode_address(address_str):
    try:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={requests.utils.quote(address_str)}&addressdetails=1"
        headers = {'User-Agent': 'CommunityHero/1.0 (contact@example.com)'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data:
                first = data[0]
                lat = float(first.get('lat'))
                lon = float(first.get('lon'))
                address = first.get('address', {})
                district = (address.get('county') or address.get('city_district') or 
                            address.get('state_district') or address.get('city') or None)
                state = address.get('state') or None
                return lat, lon, district, state
    except Exception as e:
        print(f"Forward Geocoding error: {e}")
    return None, None, None, None

def reverse_geocode(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1"
        headers = {'User-Agent': 'CommunityHero/1.0 (contact@example.com)'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            address = data.get('address', {})
            district = (address.get('county') or address.get('city_district') or 
                        address.get('state_district') or address.get('city') or None)
            state = address.get('state') or None
            return district, state
    except Exception as e:
        print(f"Reverse Geocoding error: {e}")
    return None, None

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'community-hero-super-secret-key-123')

# Parse Supabase Database URL (convert postgres:// to postgresql:// for SQLAlchemy)
db_url = os.environ.get('DATABASE_URL')
if db_url:
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
else:
    db_url = 'sqlite:///community_hero.db'

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Supabase Client if credentials are provided for storage
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase_client = None
if supabase_url and supabase_key:
    try:
        supabase_client = create_client(supabase_url, supabase_key)
        print("Supabase client initialized successfully for storage.")
    except Exception as e:
        print(f"Failed to initialize Supabase client: {e}")

# Configure Upload Folder
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB max upload size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_brevo_email(to_email, to_name, subject, html_content, reply_to_email=None, reply_to_name=None):
    api_key = os.environ.get("BREVO_API_KEY")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "notifications@community-hero.org")
    sender_name = os.environ.get("BREVO_SENDER_NAME", "Community Hero")
    
    if not api_key or api_key == "xkeysib-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" or api_key.strip() == "":
        print(f"[Brevo Email Bypass] API key is missing or dummy. Mock sending email to {to_email} with subject: {subject}")
        return True
        
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    
    data = {
        "sender": {
            "name": sender_name,
            "email": sender_email
        },
        "to": [
            {
                "email": to_email,
                "name": to_name
            }
        ],
        "subject": subject,
        "htmlContent": html_content
    }
    
    if reply_to_email:
        data["replyTo"] = {
            "email": reply_to_email,
            "name": reply_to_name or reply_to_email
        }
        
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code in [200, 201, 202]:
            print(f"Brevo Email sent successfully to {to_email}. Status code: {response.status_code}")
            return True
        else:
            print(f"Failed to send email to {to_email}. Status code: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        print(f"Error sending email via Brevo: {e}")
        return False


def fallback_heuristic_categorize(title, description):
    """
    Local heuristic rule-based categorizer fallback when Gemini API key is missing or fails.
    """
    text = (title + " " + description).lower()
    if any(word in text for word in ["pothole", "road", "street", "crack", "asphalt", "sidewalk", "pavement", "potholes"]):
        return "Roads"
    elif any(word in text for word in ["water", "leak", "pipe", "sewage", "drain", "flood", "overflow", "burst", "leakage"]):
        return "Water & Sewerage"
    elif any(word in text for word in ["garbage", "waste", "trash", "dump", "litter", "recycle", "bin", "refuse", "plastic"]):
        return "Waste Management"
    elif any(word in text for word in ["light", "dark", "lamp", "streetlight", "bulb", "darkness"]):
        return "Streetlights"
    elif any(word in text for word in ["wire", "electricity", "power", "cable", "pole", "blackout", "utility"]):
        return "Utilities"
    return "Other"

def ai_categorize(title, description):
    """
    Categorize issues using the Gemini API. Falls back to a heuristic if key is missing or model fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Gemini API key not found. Using local heuristic categorizer.")
        return fallback_heuristic_categorize(title, description)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = (
            "You are an AI assistant for a hyperlocal issue reporting application named Community Hero.\n"
            "Analyze the following reported issue:\n"
            f"Title: {title}\n"
            f"Description: {description}\n\n"
            "Classify it into exactly one of these categories:\n"
            "- Roads\n"
            "- Water & Sewerage\n"
            "- Waste Management\n"
            "- Streetlights\n"
            "- Utilities\n"
            "- Other\n\n"
            "Output only the category name exactly as written above, without quotes, formatting, or extra text."
        )
        
        response = model.generate_content(prompt)
        category = response.text.strip()
        
        allowed_categories = ['Roads', 'Water & Sewerage', 'Waste Management', 'Streetlights', 'Utilities', 'Other']
        if category in allowed_categories:
            return category
            
        # Flexible matching in case of formatting
        for cat in allowed_categories:
            if cat.lower() in category.lower():
                return cat
                
        return "Other"
    except Exception as e:
        print(f"Gemini API Error: {e}. Falling back to local heuristic.")
        return fallback_heuristic_categorize(title, description)

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/map')
@login_required
def index():
    if current_user.role in ['state_manager', 'admin']:
        if 'inspect_district' in session:
            return render_template('index.html', 
                                   inspecting=True, 
                                   inspect_district=session['inspect_district'], 
                                   inspect_state=session['inspect_state'])
        else:
            return redirect(url_for('dashboard'))
    return render_template('index.html', inspecting=False)

@app.route('/api/stats', methods=['GET'])
def api_stats():
    resolved = Issue.query.filter((Issue.status == 'Resolved') | (Issue.govt_status == 'DONE')).count()
    citizens = User.query.filter_by(role='citizen').count()
    districts = db.session.query(Issue.district).filter(Issue.district != None).distinct().all()
    dist_set = set(d[0] for d in districts if d[0])
    user_districts = db.session.query(User.district).filter(User.district != None, User.role == 'district_manager').distinct().all()
    for d in user_districts:
        if d[0]:
            dist_set.add(d[0])
    return jsonify({
        'resolved': resolved,
        'citizens': citizens,
        'districts': len(dist_set)
    })

@app.route('/inspect/state/<string:state>')
@login_required
def inspect_state(state):
    if current_user.role != 'admin':
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard'))
    session['inspect_state'] = state
    session.pop('inspect_district', None)
    flash(f"Now inspecting state: {state}", 'info')
    return redirect(url_for('dashboard'))

@app.route('/inspect/district/<string:district>/<string:state>')
@login_required
def inspect_district(district, state):
    if current_user.role == 'admin':
        session['inspect_state'] = state
        session['inspect_district'] = district
    elif current_user.role == 'state_manager':
        if current_user.state != state:
            flash('Unauthorized state district access.', 'error')
            return redirect(url_for('dashboard'))
        session['inspect_state'] = state
        session['inspect_district'] = district
    else:
        flash('Unauthorized.', 'error')
        return redirect(url_for('dashboard'))
        
    flash(f"Now inspecting district: {district}, {state}", 'info')
    return redirect(url_for('index'))

@app.route('/exit_state_inspection')
@login_required
def exit_state_inspection():
    session.pop('inspect_state', None)
    session.pop('inspect_district', None)
    flash('Exited state inspection.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/exit_district_inspection')
@login_required
def exit_district_inspection():
    session.pop('inspect_district', None)
    flash('Exited district inspection.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            if user.role in ['state_manager', 'admin']:
                return redirect(url_for('dashboard'))
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        address = request.form.get('address')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
            
        if not address or len(address.strip()) == 0:
            flash('Home address is required.', 'error')
            return render_template('register.html')
            
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')
            
        # Geocode home address
        lat, lon, district, state = geocode_address(address)
        if lat is None or lon is None:
            lat, lon = 12.9716, 77.5946
        if not district:
            district = "Bangalore Urban"
        if not state:
            state = "Karnataka"
        
        user = User(
            username=username, 
            email=email, 
            role='citizen', 
            points=50,
            address=address,
            latitude=lat,
            longitude=lon,
            district=district,
            state=state
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Send professional onboarding email
        subject = "Welcome to Community Hero!"
        html_content = f"""
        <html>
            <body>
                <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 30px 15px; margin: 0; min-height: 100%;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 25px; text-align: center; border-bottom: 3px solid #00f2fe;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 1.5rem; letter-spacing: 1px; font-weight: 700;">WELCOME TO COMMUNITY HERO</h1>
                        </div>
                        <div style="padding: 30px 25px; color: #334155; line-height: 1.6; font-size: 1rem;">
                            <p style="margin-top: 0;">Hello <strong>{username}</strong>,</p>
                            <p>Thank you for joining the <strong>Community Hero</strong> initiative! Your account has been registered successfully.</p>

                            <h3 style="color: #0f172a; font-size: 1.05rem; margin-top: 25px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px;">How to Earn Points & Climb the Leaderboard</h3>
                            <p>Every contribution counts! Here is how you can earn civic status points:</p>
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; margin: 15px 0;">
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">Sign Up Bonus</td>
                                    <td style="padding: 8px 0; text-align: right; color: #00875a; font-weight: bold;">+50 Points</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">Reporting a Local Issue</td>
                                    <td style="padding: 8px 0; text-align: right; color: #00875a; font-weight: bold;">+15 Points</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">Upvoting/Downvoting an Issue</td>
                                    <td style="padding: 8px 0; text-align: right; color: #00875a; font-weight: bold;">+5 Points</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">Commenting on an Issue</td>
                                    <td style="padding: 8px 0; text-align: right; color: #00875a; font-weight: bold;">+2 Points</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">Successful Gov't Issue Resolution</td>
                                    <td style="padding: 8px 0; text-align: right; color: #00875a; font-weight: bold;">+50 Points</td>
                                </tr>
                            </table>

                            <p style="margin-top: 25px; margin-bottom: 0; text-align: center;">
                                <a href="{os.environ.get('WEB_LINK_GCP', '#')}" style="background-color: #0f172a; color: #ffffff; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.15);">Get Started - View Map</a>
                            </p>
                        </div>
                        <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 0.8rem; color: #64748b; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0 0 5px 0; font-weight: 600;">Community Hero Initiative</p>
                            <p style="margin: 0;">This operational email was sent to confirm your civic registration.</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        send_brevo_email(email, username, subject, html_content)
        
        login_user(user)
        flash(f'Account created! Home resolved to: {district}, {state}. (+50 Pts)', 'success')
        return redirect(url_for('index'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('inspect_state', None)
    session.pop('inspect_district', None)
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    if current_user.role != 'citizen':
        flash('Only citizens can update their profile here.', 'error')
        return redirect(url_for('dashboard'))

    email = request.form.get('email')
    address = request.form.get('address')
    
    updated = False
    
    if email and email != current_user.email:
        if current_user.email_updated_at:
            days_since_update = (datetime.utcnow() - current_user.email_updated_at).days
            if days_since_update < 30:
                flash(f'Email can only be updated once a month. Try again in {30 - days_since_update} days.', 'error')
                return redirect(url_for('dashboard'))
                
        if User.query.filter_by(email=email).first():
            flash('Email already registered by another user.', 'error')
            return redirect(url_for('dashboard'))
            
        current_user.email = email
        current_user.email_updated_at = datetime.utcnow()
        updated = True
        
    if address and address != current_user.address:
        if current_user.address_updated_at:
            days_since_update = (datetime.utcnow() - current_user.address_updated_at).days
            if days_since_update < 30:
                flash(f'Address can only be updated once a month. Try again in {30 - days_since_update} days.', 'error')
                return redirect(url_for('dashboard'))
                
        current_user.address = address
        lat, lon, district, state = geocode_address(address)
        current_user.latitude = lat
        current_user.longitude = lon
        current_user.district = district
        current_user.state = state
        current_user.address_updated_at = datetime.utcnow()
        updated = True
        
    if updated:
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    else:
        flash('No changes were made to your profile.', 'info')
        
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'district_manager':
        return redirect(url_for('index'))
        
    elif current_user.role == 'state_manager':
        state = current_user.state
        districts_data = []
        # Distinct districts from issues and users in this state
        districts = db.session.query(Issue.district).filter_by(state=state).distinct().all()
        districts = [d[0] for d in districts if d[0]]
        user_districts = db.session.query(User.district).filter_by(state=state, role='district_manager').distinct().all()
        districts = list(set(districts + [d[0] for d in user_districts if d[0]]))
        
        for dist in districts:
            total = Issue.query.filter_by(state=state, district=dist).count()
            completed = Issue.query.filter_by(state=state, district=dist, govt_status='DONE').count()
            rate = (completed / total * 100) if total > 0 else 0
            districts_data.append({
                'district': dist,
                'total_issues': total,
                'completion_rate': round(rate, 1)
            })
            
        district_managers = User.query.filter_by(role='district_manager', state=state).all()
        return render_template('dashboard.html', 
                               districts_data=districts_data, 
                               district_managers=district_managers,
                               state=state)
                               
    elif current_user.role == 'admin':
        # Admin dashboard can inspect states
        inspect_state_val = session.get('inspect_state')
        if inspect_state_val:
            # Render state manager view for the inspected state
            districts_data = []
            districts = db.session.query(Issue.district).filter_by(state=inspect_state_val).distinct().all()
            districts = [d[0] for d in districts if d[0]]
            user_districts = db.session.query(User.district).filter_by(state=inspect_state_val, role='district_manager').distinct().all()
            districts = list(set(districts + [d[0] for d in user_districts if d[0]]))
            
            for dist in districts:
                total = Issue.query.filter_by(state=inspect_state_val, district=dist).count()
                completed = Issue.query.filter_by(state=inspect_state_val, district=dist, govt_status='DONE').count()
                rate = (completed / total * 100) if total > 0 else 0
                districts_data.append({
                    'district': dist,
                    'total_issues': total,
                    'completion_rate': round(rate, 1)
                })
                
            district_managers = User.query.filter_by(role='district_manager', state=inspect_state_val).all()
            return render_template('dashboard.html', 
                                   districts_data=districts_data, 
                                   district_managers=district_managers,
                                   state=inspect_state_val,
                                   inspecting_state=True)
        else:
            # Render general admin list of states
            states_data = []
            all_states = db.session.query(Issue.state).distinct().all()
            all_states = [s[0] for s in all_states if s[0]]
            user_states = db.session.query(User.state).distinct().all()
            all_states = list(set(all_states + [s[0] for s in user_states if s[0]]))
            
            for st in all_states:
                total_issues = Issue.query.filter_by(state=st).count()
                completed_issues = Issue.query.filter_by(state=st, govt_status='DONE').count()
                completion_rate = (completed_issues / total_issues * 100) if total_issues > 0 else 0
                districts_count = db.session.query(Issue.district).filter_by(state=st).distinct().count()
                managers_count = User.query.filter_by(role='state_manager', state=st).count()
                states_data.append({
                    'state': st,
                    'total_issues': total_issues,
                    'districts_count': districts_count,
                    'completion_rate': round(completion_rate, 1),
                    'managers_count': managers_count
                })
            # Query issues in states with no district managers
            states_with_issues = db.session.query(Issue.state).distinct().all()
            states_with_issues = [s[0] for s in states_with_issues if s[0]]
            
            unassigned_alerts = []
            for st in states_with_issues:
                has_dm = User.query.filter_by(role='district_manager', state=st).first() is not None
                if not has_dm:
                    state_issues = Issue.query.filter_by(state=st).order_by(Issue.created_at.desc()).all()
                    for issue in state_issues:
                        unassigned_alerts.append({
                            'id': issue.id,
                            'title': issue.title,
                            'description': issue.description,
                            'district': issue.district,
                            'state': issue.state,
                            'created_at': issue.created_at.strftime('%Y-%m-%d %H:%M'),
                            'reporter': issue.reporter.username
                        })

            state_managers = User.query.filter_by(role='state_manager').all()
            return render_template('dashboard.html', 
                                   states_data=states_data, 
                                   state_managers=state_managers,
                                   unassigned_alerts=unassigned_alerts)
                                   
    else: # Citizen
        user_issues = Issue.query.filter_by(user_id=current_user.id).order_by(Issue.created_at.desc()).all()
        return render_template('dashboard.html', issues=user_issues)

@app.route('/leaderboard')
@login_required
def leaderboard():
    # 1. Top citizens
    users = User.query.filter_by(role='citizen').order_by(User.points.desc()).limit(10).all()
    
    # Fetch all unique states to populate the filter dropdown
    unique_states_query = db.session.query(User.state).filter(User.state != None, User.state != '').distinct().all()
    unique_states = [r[0] for r in unique_states_query]
    # Ensure standard states are listed if they exist or as seed references
    for default_state in ['Karnataka', 'Maharashtra', 'Delhi']:
        if default_state not in unique_states:
            unique_states.append(default_state)
    unique_states.sort()

    # 2. State Districts Performance Leaderboard
    state_query = request.args.get('state')
    if not state_query:
        if current_user.role == 'admin':
            state_query = 'All'
        else:
            state_query = current_user.state or 'Karnataka'

    # Compute standings and absolute ranks on a GLOBAL scale first (to preserve absolute rank during filtering)
    global_issues = Issue.query.all()
    global_totals = {}
    global_completed = {}
    global_states = {}

    for issue in global_issues:
        d = issue.district or 'Unknown'
        s = issue.state or 'Unknown'
        global_totals[d] = global_totals.get(d, 0) + 1
        global_states[d] = s
        if issue.govt_status == 'DONE' or issue.status == 'Resolved':
            global_completed[d] = global_completed.get(d, 0) + 1
            
    # Include all district managers globally to capture inactive/new districts
    managers_dist_all = db.session.query(User.district, User.state).filter_by(role='district_manager').distinct().all()
    for row in managers_dist_all:
        dist_name, state_name = row
        if dist_name and dist_name not in global_totals:
            global_totals[dist_name] = 0
            global_states[dist_name] = state_name or 'Unknown'
            
    global_standings = []
    for d, total in global_totals.items():
        completed = global_completed.get(d, 0)
        rate = (completed / total * 100) if total > 0 else 0
        global_standings.append({
            'district': d,
            'state': global_states.get(d, 'Unknown'),
            'total': total,
            'completed': completed,
            'rate': round(rate, 1)
        })
    global_standings.sort(key=lambda x: x['rate'], reverse=True)
    
    # Assign absolute global ranks (1-indexed)
    for idx, item in enumerate(global_standings):
        item['global_rank'] = idx + 1

    # Filter district standings based on the selected state query
    if state_query == 'All':
        district_standings = global_standings
    else:
        district_standings = [item for item in global_standings if item['state'] == state_query]
    
    # 3. Inter-State Leaderboard
    all_issues = Issue.query.all()
    state_totals = {}
    state_completed = {}
    for issue in all_issues:
        s = issue.state or 'Unknown'
        state_totals[s] = state_totals.get(s, 0) + 1
        if issue.govt_status == 'DONE' or issue.status == 'Resolved':
            state_completed[s] = state_completed.get(s, 0) + 1
            
    # Include users' states
    states_list = db.session.query(User.state).distinct().all()
    for row in states_list:
        if row[0] and row[0] not in state_totals:
            state_totals[row[0]] = 0
            
    state_standings = []
    for s, total in state_totals.items():
        completed = state_completed.get(s, 0)
        rate = (completed / total * 100) if total > 0 else 0
        state_standings.append({
            'state': s,
            'total': total,
            'completed': completed,
            'rate': round(rate, 1)
        })
    state_standings.sort(key=lambda x: x['rate'], reverse=True)
    
    return render_template('leaderboard.html', 
                           users=users,
                           district_standings=district_standings,
                           state_standings=state_standings,
                           selected_state=state_query,
                           unique_states=unique_states)

@app.route('/stats')
@login_required
def stats():
    selected_state = None
    selected_district = None
    states_list = []
    districts_list = []

    if current_user.role == 'admin':
        # Admin gets state-level stats & selection of all states
        states = db.session.query(Issue.state).filter(Issue.state != None).distinct().all()
        states_list = sorted([s[0] for s in states if s[0]])
        selected_state = request.args.get('state')
        if not selected_state and states_list:
            selected_state = states_list[0]
            
    elif current_user.role == 'state_manager':
        # State Manager gets district-level statistics in their state
        selected_state = current_user.state
        districts = db.session.query(Issue.district).filter_by(state=selected_state).filter(Issue.district != None).distinct().all()
        districts_list = sorted([d[0] for d in districts if d[0]])
        selected_district = request.args.get('district')
        if not selected_district and districts_list:
            selected_district = districts_list[0]
            
    elif current_user.role in ['district_manager', 'citizen']:
        # District Manager and Citizen get their home district details
        selected_state = current_user.state
        selected_district = current_user.district

    # Query issues matching selected filters
    query = Issue.query
    if selected_state:
        query = query.filter_by(state=selected_state)
    if selected_district:
        query = query.filter_by(district=selected_district)
        
    issues = query.all()
    
    total_issues = len(issues)
    resolved_issues = sum(1 for i in issues if i.status == 'Resolved' or i.govt_status == 'DONE')
    open_issues = total_issues - resolved_issues
    resolution_rate = round((resolved_issues / total_issues * 100), 1) if total_issues > 0 else 0.0
    
    # Category distribution
    categories = ['Roads', 'Water & Sewerage', 'Waste Management', 'Streetlights', 'Utilities', 'Other']
    cat_counts = {cat: 0 for cat in categories}
    for i in issues:
        cat = i.category if i.category in categories else 'Other'
        cat_counts[cat] += 1

    # Additional Analytics: Intensity ratios
    high_count = sum(1 for i in issues if i.intensity == 'High')
    med_count = sum(1 for i in issues if i.intensity == 'Medium')
    low_count = sum(1 for i in issues if i.intensity == 'Low')

    # Community Engagement: average comments & votes per issue
    avg_comments = 0.0
    avg_votes = 0.0
    if total_issues > 0:
        total_comments = sum(len(i.comments) for i in issues)
        total_votes = sum(len(i.votes) for i in issues)
        avg_comments = round(total_comments / total_issues, 1)
        avg_votes = round(total_votes / total_issues, 1)
        
    # Serialize coordinate details for vector Leaflet heat mapping
    issues_json = []
    for i in issues:
        if i.latitude is not None and i.longitude is not None:
            issues_json.append({
                'title': i.title,
                'category': i.category,
                'intensity': i.intensity,
                'latitude': i.latitude,
                'longitude': i.longitude,
                'status': i.status
            })
            
    return render_template('stats.html', 
                           total_issues=total_issues,
                           resolved_issues=resolved_issues,
                           open_issues=open_issues,
                           resolution_rate=resolution_rate,
                           cat_counts=cat_counts,
                           high_count=high_count,
                           med_count=med_count,
                           low_count=low_count,
                           avg_comments=avg_comments,
                           avg_votes=avg_votes,
                           issues_json=issues_json,
                           states_list=states_list,
                           districts_list=districts_list,
                           selected_state=selected_state,
                           selected_district=selected_district)

# --- API ENDPOINTS ---

@app.route('/api/issues', methods=['GET'])
@login_required
def get_issues():
    target_district = None
    target_state = None
    
    if current_user.role == 'district_manager':
        target_district = current_user.district
        target_state = current_user.state
    elif current_user.role in ['state_manager', 'admin']:
        if 'inspect_district' in session:
            target_district = session['inspect_district']
            target_state = session['inspect_state']
        else:
            target_district = request.args.get('district')
            target_state = request.args.get('state')
            
            if current_user.role == 'state_manager' and target_state and target_state != current_user.state:
                return jsonify({'error': 'Unauthorized state scope'}), 403
                
    if current_user.role == 'district_manager':
        all_state_issues = Issue.query.filter_by(state=current_user.state).all()
        state_managers = User.query.filter_by(role='district_manager', state=current_user.state).all()
        
        filtered_issues = []
        for issue in all_state_issues:
            if issue.district == current_user.district:
                filtered_issues.append(issue)
            else:
                district_has_manager = any(m.district == issue.district for m in state_managers)
                if not district_has_manager:
                    closest_mgr = None
                    min_dist = float('inf')
                    for m in state_managers:
                        m_lat, m_lon = m.latitude, m.longitude
                        if m_lat is None or m_lon is None:
                            m_lat, m_lon, _, _ = geocode_address(f"{m.district}, {m.state}")
                            if m_lat is not None and m_lon is not None:
                                m.latitude = m_lat
                                m.longitude = m_lon
                                db.session.add(m)
                                db.session.commit()
                        
                        if m_lat is not None and m_lon is not None:
                            dist = haversine_distance(issue.latitude, issue.longitude, m_lat, m_lon)
                            if dist < min_dist:
                                min_dist = dist
                                closest_mgr = m
                                
                    if closest_mgr and closest_mgr.id == current_user.id:
                        filtered_issues.append(issue)
        issues = filtered_issues
        issues.sort(key=lambda x: x.created_at, reverse=True)
    else:
        query = Issue.query
        if target_district:
            query = query.filter_by(district=target_district)
        if target_state:
            query = query.filter_by(state=target_state)
        issues = query.order_by(Issue.created_at.desc()).all()
    output = []
    for issue in issues:
        # Determine if current user voted
        user_vote = Vote.query.filter_by(issue_id=issue.id, user_id=current_user.id).first()
        voted = user_vote.vote_type if user_vote else None
        
        # Build comments list
        comments_list = []
        for c in issue.comments:
            comments_list.append({
                'author': c.author.username,
                'content': c.content,
                'created_at': c.created_at.strftime('%Y-%m-%d %H:%M')
            })
            
        # Build update logs list
        logs_list = []
        for log in issue.update_logs:
            logs_list.append({
                'author': log.logger.username,
                'content': log.content,
                'status_update': log.status_update,
                'created_at': log.created_at.strftime('%Y-%m-%d %H:%M')
            })

        img_url = None
        if issue.image_filename:
            if issue.image_filename.startswith('http'):
                img_url = issue.image_filename
            else:
                img_url = url_for('static', filename='uploads/' + issue.image_filename)

        output.append({
            'id': issue.id,
            'title': issue.title,
            'description': issue.description,
            'intensity': issue.intensity,
            'category': issue.category,
            'latitude': issue.latitude,
            'longitude': issue.longitude,
            'image_url': img_url,
            'status': issue.status,
            'govt_status': issue.govt_status,
            'govt_status_updated_at': issue.govt_status_updated_at.strftime('%Y-%m-%d %H:%M') if issue.govt_status_updated_at else None,
            'created_at': issue.created_at.strftime('%Y-%m-%d %H:%M'),
            'reporter': issue.reporter.username,
            'reporter_id': issue.user_id,
            'reporter_points': issue.reporter.points,
            'score': issue.vote_score,
            'user_vote': voted,
            'district': issue.district,
            'state': issue.state,
            'comments': comments_list,
            'logs': logs_list
        })
    return jsonify(output)

@app.route('/api/issues/report', methods=['POST'])
@login_required
def report_issue():
    if current_user.role != 'citizen':
        return jsonify({'error': 'Managers and administrators are not permitted to report issues.'}), 403
        
    title = request.form.get('title')
    description = request.form.get('description')
    intensity = request.form.get('intensity', 'Medium')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    user_lat = request.form.get('user_latitude')
    user_lng = request.form.get('user_longitude')
    
    if not title or not description or not latitude or not longitude:
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        latitude = float(latitude)
        longitude = float(longitude)
        user_lat = float(user_lat) if user_lat else None
        user_lng = float(user_lng) if user_lng else None
    except ValueError:
        return jsonify({'error': 'Invalid coordinates'}), 400

    # Range Check: Must be within 10 km of current GPS location
    if user_lat is None or user_lng is None:
        return jsonify({'error': 'Current GPS location is required to verify the 10 KM reporting range.'}), 400
        
    dist_to_gps = haversine_distance(latitude, longitude, user_lat, user_lng)
    if dist_to_gps > 10.0:
        return jsonify({'error': 'Cannot report an issue located more than 10 KM away from your current location.'}), 400

    # Auto categorization using Gemini API (with local rule fallback)
    category = ai_categorize(title, description)
    
    uploaded_urls = []
    if 'image' in request.files:
        files = request.files.getlist('image')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file.filename}")
                
                if supabase_client:
                    try:
                        file_data = file.read()
                        content_type = file.mimetype
                        supabase_client.storage.from_('issue-media').upload(
                            path=filename,
                            file=file_data,
                            file_options={"content-type": content_type}
                        )
                        url = supabase_client.storage.from_('issue-media').get_public_url(filename)
                        uploaded_urls.append(url)
                    except Exception as e:
                        print(f"Supabase storage upload failed: {e}. Falling back to local storage.")
                        file.seek(0)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        uploaded_urls.append(filename)
                    finally:
                        file.close()
                else:
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    uploaded_urls.append(filename)
                    file.close()
                    
    image_filename = ",".join(uploaded_urls) if uploaded_urls else None

    # Reverse geocode the issue coordinate to get district and state
    issue_district, issue_state = reverse_geocode(latitude, longitude)
    if not issue_district or not issue_state or issue_district == "Unknown District" or issue_state == "Unknown State":
        issue_district = current_user.district
        issue_state = current_user.state

    if current_user.role == 'citizen':
        if issue_district != current_user.district or issue_state != current_user.state:
            return jsonify({'error': f"Cannot report issues outside your registered area ({current_user.district}, {current_user.state})."}), 403

    # Dynamic manager routing logic
    state_managers = User.query.filter_by(role='district_manager', state=issue_state).all()
    assigned_manager = None
    notice_to_admin = False
    routing_msg = ""

    if state_managers:
        exact_manager = next((m for m in state_managers if m.district == issue_district), None)
        if exact_manager:
            assigned_manager = exact_manager
            routing_msg = f"Assigned directly to district manager @{assigned_manager.username}."
        else:
            min_dist = float('inf')
            for m in state_managers:
                m_lat, m_lon = m.latitude, m.longitude
                if m_lat is None or m_lon is None:
                    m_lat, m_lon, _, _ = geocode_address(f"{m.district}, {m.state}")
                    if m_lat is not None and m_lon is not None:
                        m.latitude = m_lat
                        m.longitude = m_lon
                        db.session.add(m)
                
                if m_lat is not None and m_lon is not None:
                    dist = haversine_distance(latitude, longitude, m_lat, m_lon)
                    if dist < min_dist:
                        min_dist = dist
                        assigned_manager = m
            
            if assigned_manager:
                routing_msg = f"No manager assigned in {issue_district}. Routed to closest manager @{assigned_manager.username} ({round(min_dist, 1)} km away)."
            else:
                notice_to_admin = True
                routing_msg = f"No manager coordinates available in {issue_state}. Routed to System Admin."
    else:
        notice_to_admin = True
        routing_msg = f"No district manager is assigned yet in {issue_state}. Routed to System Admin."

    issue = Issue(
        title=title,
        description=description,
        intensity=intensity,
        category=category,
        latitude=latitude,
        longitude=longitude,
        image_filename=image_filename,
        status='Open',
        user_id=current_user.id,
        state=issue_state,
        district=issue_district,
        govt_status='NOT VISITED'
    )
    
    # Award points to reporting user
    current_user.points += 15
    
    db.session.add(issue)
    
    # Log initial report
    log = UpdateLog(
        issue=issue,
        user_id=current_user.id,
        content="Issue reported to the community.",
        status_update="Open"
    )
    db.session.add(log)
    db.session.commit()

    # Send confirmation email to the reporter
    if current_user.email:
        subject = f"[Community Hero] Confirmation: Issue #{issue.id} Reported"
        html_content = f"""
        <html>
            <body>
                <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 30px 15px; margin: 0; min-height: 100%;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 25px; text-align: center; border-bottom: 3px solid #00f2fe;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 1.5rem; letter-spacing: 1px; font-weight: 700;">REPORT RECEIVED</h1>
                        </div>
                        <div style="padding: 30px 25px; color: #334155; line-height: 1.6; font-size: 1rem;">
                            <p style="margin-top: 0;">Hello <strong>{current_user.username}</strong>,</p>
                            <p>Thank you for submitting a report to the <strong>Community Hero</strong> initiative! We have successfully registered your report for: <strong style="color: #0f172a;">"{issue.title}"</strong>.</p>
                            
                            <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; border-radius: 6px; margin: 20px 0;">
                                <h3 style="margin-top: 0; color: #0f172a; font-size: 0.95rem;">Report Details:</h3>
                                <ul style="margin: 0; padding-left: 20px; color: #475569; font-size: 0.9rem;">
                                    <li><strong>Category:</strong> {issue.category}</li>
                                    <li><strong>Intensity:</strong> {issue.intensity}</li>
                                    <li><strong>Jurisdiction:</strong> {issue.district}, {issue.state}</li>
                                    <li><strong>Status:</strong> {issue.status}</li>
                                </ul>
                            </div>
                            
                            <p>Our district management team will review this report and keep you updated as status changes are made.</p>
                        </div>
                        <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 0.8rem; color: #64748b; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0 0 5px 0; font-weight: 600;">Community Hero Initiative</p>
                            <p style="margin: 0;">This operational email confirms your civic report submission.</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        send_brevo_email(current_user.email, current_user.username, subject, html_content)
    
    # Send email alerts to admin (if no manager in state) or to the assigned manager
    if notice_to_admin:
        admins = User.query.filter_by(role='admin').all()
        for admin in admins:
            if admin.email:
                admin_subject = f"[URGENT Notice] No District Manager in {issue_state} - Issue #{issue.id}"
                admin_html = f"""
                <html>
                    <body style="font-family: sans-serif; background-color: #0b0f19; color: #f8fafc; padding: 25px;">
                        <div style="max-width: 600px; margin: 0 auto; background-color: #111827; border: 1px solid #ef4444; border-radius: 12px; padding: 30px; box-shadow: 0 4px 20px rgba(239, 68, 68, 0.15);">
                            <h2 style="color: #ef4444; margin-top: 0; font-family: 'Segoe UI', Arial, sans-serif; font-weight: 800; border-bottom: 2px solid #ef4444; padding-bottom: 10px; text-transform: uppercase; letter-spacing: 0.05em;">🚨 URGENT: JURISDICTION ALERTACT</h2>
                            <p style="font-size: 1.15rem; font-weight: 800; color: #ef4444; margin-bottom: 20px;">
                                [Notice] No district manager is assigned yet in {issue_state} state.
                            </p>
                            <div style="background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.1); padding: 15px 20px; border-radius: 8px; margin-bottom: 20px;">
                                <h3 style="margin-top: 0; color: #00f2fe; font-size: 1rem;">Issue Details:</h3>
                                <ul style="margin: 0; padding-left: 20px; color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;">
                                    <li><strong>Title:</strong> {issue.title}</li>
                                    <li><strong>Description:</strong> {issue.description}</li>
                                    <li><strong>District:</strong> {issue_district}</li>
                                    <li><strong>State:</strong> {issue_state}</li>
                                    <li><strong>Reporter:</strong> @{current_user.username}</li>
                                </ul>
                            </div>
                            <p style="color: #94a3b8; font-size: 0.9rem; line-height: 1.5;">
                                Please log in to your System Admin Dashboard to register/assign state or district managers for the {issue_state} jurisdiction area.
                            </p>
                        </div>
                    </body>
                </html>
                """
                send_brevo_email(admin.email, admin.username, admin_subject, admin_html)
    elif assigned_manager:
        if assigned_manager.email:
            if assigned_manager.district != issue_district:
                mgr_subject = f"[Community Hero] Fallback Routing Notice: Issue #{issue.id}"
                mgr_html = f"""
                <html>
                    <body style="font-family: sans-serif; background-color: #0b0f19; color: #f8fafc; padding: 25px;">
                        <div style="max-width: 600px; margin: 0 auto; background-color: #111827; border: 1px solid #f59e0b; border-radius: 12px; padding: 30px; box-shadow: 0 4px 20px rgba(245, 158, 11, 0.15);">
                            <h2 style="color: #f59e0b; margin-top: 0; font-family: 'Segoe UI', Arial, sans-serif; font-weight: 800; border-bottom: 2px solid #f59e0b; padding-bottom: 10px; text-transform: uppercase;">⚠️ FALLBACK JURISDICTION ROUTING</h2>
                            <p style="font-size: 1.05rem; font-weight: 700; color: #fbbf24; margin-bottom: 20px;">
                                An issue was reported in {issue_district}, {issue_state}. Since no district manager is assigned to {issue_district}, this issue has been routed to you as the closest manager in the state.
                            </p>
                            <div style="background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.1); padding: 15px 20px; border-radius: 8px; margin-bottom: 20px;">
                                <h3 style="margin-top: 0; color: #00f2fe; font-size: 1rem;">Issue Details:</h3>
                                <ul style="margin: 0; padding-left: 20px; color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;">
                                    <li><strong>Title:</strong> {issue.title}</li>
                                    <li><strong>Description:</strong> {issue.description}</li>
                                    <li><strong>Reporter:</strong> @{current_user.username}</li>
                                </ul>
                            </div>
                        </div>
                    </body>
                </html>
                """
            else:
                mgr_subject = f"[Community Hero] New Issue Assigned: #{issue.id}"
                mgr_html = f"""
                <html>
                    <body style="font-family: sans-serif; background-color: #0b0f19; color: #f8fafc; padding: 25px;">
                        <div style="max-width: 600px; margin: 0 auto; background-color: #111827; border: 1px solid #00f2fe; border-radius: 12px; padding: 30px; box-shadow: 0 4px 20px rgba(0, 242, 254, 0.15);">
                            <h2 style="color: #00f2fe; margin-top: 0; font-family: 'Segoe UI', Arial, sans-serif; font-weight: 800; border-bottom: 2px solid #00f2fe; padding-bottom: 10px; text-transform: uppercase;">📥 NEW ISSUE JURISDICTION</h2>
                            <p style="font-size: 1.05rem; font-weight: 700; color: #f8fafc; margin-bottom: 20px;">
                                A new issue has been reported in your district: {issue_district}.
                            </p>
                            <div style="background-color: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.1); padding: 15px 20px; border-radius: 8px; margin-bottom: 20px;">
                                <h3 style="margin-top: 0; color: #00f2fe; font-size: 1rem;">Issue Details:</h3>
                                <ul style="margin: 0; padding-left: 20px; color: #cbd5e1; font-size: 0.95rem; line-height: 1.6;">
                                    <li><strong>Title:</strong> {issue.title}</li>
                                    <li><strong>Description:</strong> {issue.description}</li>
                                    <li><strong>Reporter:</strong> @{current_user.username}</li>
                                </ul>
                            </div>
                        </div>
                    </body>
                </html>
                """
            send_brevo_email(assigned_manager.email, assigned_manager.username, mgr_subject, mgr_html)

    return jsonify({
        'success': True,
        'message': f'Issue reported! {routing_msg} Auto-categorized: {category}. +15 Pts!',
        'issue_id': issue.id,
        'category': category
    })

@app.route('/api/issues/<int:issue_id>/vote', methods=['POST'])
@login_required
def vote_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    if current_user.role == 'citizen':
        if issue.district != current_user.district or issue.state != current_user.state:
            return jsonify({'error': 'You can only vote on issues within your registered area.'}), 403

    vote_type = request.json.get('vote_type')
    
    if vote_type not in ['upvote', 'downvote']:
        return jsonify({'error': 'Invalid vote type'}), 400
        
    existing_vote = Vote.query.filter_by(issue_id=issue_id, user_id=current_user.id).first()
    reporter = issue.reporter
    
    if existing_vote:
        if existing_vote.vote_type == vote_type:
            # Retract vote
            db.session.delete(existing_vote)
            # Both upvote and downvote award +5, so retracting either removes 5 points.
            reporter.points = max(0, reporter.points - 5)
            db.session.commit()
            return jsonify({'success': True, 'action': 'retracted', 'score': issue.vote_score})
        else:
            # Switch vote
            existing_vote.vote_type = vote_type
            # Since both upvote and downvote award +5, switching between them leaves reporter points unchanged.
            db.session.commit()
            return jsonify({'success': True, 'action': 'switched', 'score': issue.vote_score})
    else:
        # New vote
        new_vote = Vote(issue_id=issue_id, user_id=current_user.id, vote_type=vote_type)
        db.session.add(new_vote)
        # Both upvote and downvote award +5 points to the reporter
        reporter.points += 5
        db.session.commit()
        return jsonify({'success': True, 'action': 'voted', 'score': issue.vote_score})

@app.route('/api/issues/<int:issue_id>/comment', methods=['POST'])
@login_required
def comment_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    if current_user.role == 'citizen':
        if issue.district != current_user.district or issue.state != current_user.state:
            return jsonify({'error': 'You can only comment on issues within your registered area.'}), 403

    content = request.json.get('content')
    
    if not content or len(content.strip()) == 0:
        return jsonify({'error': 'Comment cannot be empty'}), 400
        
    comment = Comment(issue_id=issue_id, user_id=current_user.id, content=content)
    db.session.add(comment)
    
    # Award points for participation
    current_user.points += 2
    
    db.session.commit()
    return jsonify({
        'success': True,
        'comment': {
            'author': current_user.username,
            'content': content,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M')
        }
    })

@app.route('/api/issues/<int:issue_id>/govt_update', methods=['POST'])
@login_required
def govt_update_issue(issue_id):
    if current_user.role != 'district_manager':
        return jsonify({'error': 'Only district managers are authorized to update government status.'}), 403
        
    issue = Issue.query.get_or_404(issue_id)
    if issue.district != current_user.district or issue.state != current_user.state:
        return jsonify({'error': 'You do not manage this district.'}), 403
        
    govt_status = request.form.get('govt_status')
    content = request.form.get('content')
    
    if govt_status not in ['NOT VISITED', 'ONGOING', 'DONE']:
        return jsonify({'error': 'Invalid government status value.'}), 400
        
    if not content or len(content.strip()) == 0:
        return jsonify({'error': 'Please describe the status update details.'}), 400
        
    issue.govt_status = govt_status
    issue.govt_status_updated_at = datetime.utcnow()
    
    # Update regular issue status accordingly
    if govt_status == 'DONE':
        issue.status = 'Resolved'
        # Award bonus resolution points
        issue.reporter.points += 50
        current_user.points += 25
    elif govt_status == 'ONGOING':
        issue.status = 'In Progress'
        current_user.points += 5
    else:
        issue.status = 'Open'
        
    log = UpdateLog(
        issue_id=issue_id,
        user_id=current_user.id,
        content=f"Government status updated to {govt_status}. Update: {content}",
        status_update=govt_status
    )
    db.session.add(log)
    db.session.commit()
    
    # Send email notification to the reporter
    reporter = issue.reporter
    if reporter and reporter.email:
        subject = f"Update on your reported issue: {issue.title}"
        html_content = f"""
        <html>
            <body>
                <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 30px 15px; margin: 0; min-height: 100%;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 25px; text-align: center; border-bottom: 3px solid #00f2fe;">
                            <h1 style="color: #ffffff; margin: 0; font-size: 1.5rem; letter-spacing: 1px; font-weight: 700;">COMMUNITY HERO</h1>
                        </div>
                        <div style="padding: 30px 25px; color: #334155; line-height: 1.6; font-size: 1rem;">
                            <p style="margin-top: 0;">Hello <strong>{reporter.username}</strong>,</p>
                            <p>An update has been logged regarding the civic issue you reported: <strong style="color: #0f172a;">"{issue.title}"</strong>.</p>
                            
                            <div style="background-color: #f8fafc; border-left: 4px solid #00f2fe; padding: 20px; border-radius: 6px; margin: 25px 0; border-top: 1px solid #f1f5f9; border-right: 1px solid #f1f5f9; border-bottom: 1px solid #f1f5f9;">
                                <p style="margin: 0 0 12px 0;"><strong>Status:</strong> <span style="background-color: #e0f7fa; color: #006064; padding: 4px 10px; border-radius: 20px; font-size: 0.85rem; font-weight: bold;">{govt_status}</span></p>
                                <p style="margin: 0; color: #475569;"><strong>Official Log Notes:</strong><br/>{content}</p>
                            </div>
                            
                            <p style="margin-bottom: 0;">Thank you for your active participation in improving our neighborhood's safety and environment!</p>
                        </div>
                        <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 0.8rem; color: #64748b; border-top: 1px solid #e2e8f0;">
                            <p style="margin: 0 0 5px 0; font-weight: 600;">Community Hero Initiative</p>
                            <p style="margin: 0;">This is an automated operational notification. Please do not reply directly to this mail address.</p>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """
        send_brevo_email(reporter.email, reporter.username, subject, html_content)

    return jsonify({'success': True})

@app.route('/api/issues/<int:issue_id>/challenge', methods=['POST'])
@login_required
def challenge_issue(issue_id):
    if current_user.role != 'citizen':
        return jsonify({'error': 'Only citizens can challenge resolutions.'}), 403
        
    issue = Issue.query.get_or_404(issue_id)
    if issue.user_id != current_user.id:
        return jsonify({'error': 'Only the original reporter can challenge this completion.'}), 403
        
    if issue.govt_status != 'DONE':
        return jsonify({'error': 'This issue is not marked as resolved by the government.'}), 400
        
    # Check 3-month (90 days) window
    if issue.govt_status_updated_at:
        days_passed = (datetime.utcnow() - issue.govt_status_updated_at).days
        if days_passed > 90:
            return jsonify({'error': 'The challenge window of 90 days has expired.'}), 400
            
    content = request.json.get('content')
    if not content or len(content.strip()) == 0:
        return jsonify({'error': 'A reason for the challenge is required.'}), 400
        
    # Revert status
    issue.govt_status = 'NOT VISITED'
    issue.status = 'Open'
    
    log = UpdateLog(
        issue_id=issue_id,
        user_id=current_user.id,
        content=f"Citizen challenged government resolution. Reason: {content}",
        status_update="NOT VISITED"
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/issues/<int:issue_id>/contact_reporter', methods=['POST'])
@login_required
def contact_reporter(issue_id):
    if current_user.role not in ['district_manager', 'state_manager', 'admin']:
        return jsonify({'error': 'Unauthorized. Only managers/admins can contact reporters.'}), 403

    issue = Issue.query.get_or_404(issue_id)

    # If manager, check scope
    if current_user.role == 'district_manager':
        if issue.district != current_user.district or issue.state != current_user.state:
            return jsonify({'error': 'You do not manage the district where this issue was reported.'}), 403
    elif current_user.role == 'state_manager':
        if issue.state != current_user.state:
            return jsonify({'error': 'You do not manage the state where this issue was reported.'}), 403

    subject = request.json.get('subject')
    body = request.json.get('body')

    if not subject or len(subject.strip()) == 0:
        return jsonify({'error': 'Subject is required.'}), 400
    if not body or len(body.strip()) == 0:
        return jsonify({'error': 'Message body is required.'}), 400

    reporter = issue.reporter
    if not reporter or not reporter.email:
        return jsonify({'error': 'Reporter email not found.'}), 404

    # Build secure email HTML content for reporter
    html_content = f"""
    <html>
        <body>
            <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 30px 15px; margin: 0; min-height: 100%;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 25px; text-align: center; border-bottom: 3px solid #00f2fe;">
                        <h1 style="color: #ffffff; margin: 0; font-size: 1.5rem; letter-spacing: 1px; font-weight: 700;">COMMUNITY HERO</h1>
                    </div>
                    <div style="padding: 30px 25px; color: #334155; line-height: 1.6; font-size: 1rem;">
                        <p style="margin-top: 0;">Hello <strong>{reporter.username}</strong>,</p>
                        <p>An official message has been sent to you by your District Manager (<strong>{current_user.username}</strong>) regarding your reported issue: <strong style="color: #0f172a;">"{issue.title}"</strong>.</p>
                        
                        <div style="background-color: #f8fafc; border-left: 4px solid #00f2fe; padding: 20px; border-radius: 6px; margin: 25px 0; border-top: 1px solid #f1f5f9; border-right: 1px solid #f1f5f9; border-bottom: 1px solid #f1f5f9; white-space: pre-wrap;">
                            <strong style="color: #0f172a; display: block; margin-bottom: 8px;">Message:</strong>
                            {body}
                        </div>
                        
                        <p style="margin-bottom: 0;">You can reply directly to this email to communicate back with the manager securely.</p>
                    </div>
                    <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 0.8rem; color: #64748b; border-top: 1px solid #e2e8f0;">
                        <p style="margin: 0 0 5px 0; font-weight: 600;">Community Hero Secure Communications Hub</p>
                        <p style="margin: 0;">Replies to this email will be forwarded directly to the manager's registered inbox.</p>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """

    # Send to reporter, setting the Reply-To to manager's email
    sent_to_reporter = send_brevo_email(
        to_email=reporter.email,
        to_name=reporter.username,
        subject=f"[Community Hero] Manager contact re: {issue.title} - {subject}",
        html_content=html_content,
        reply_to_email=current_user.email,
        reply_to_name=current_user.username
    )

    if not sent_to_reporter:
        return jsonify({'error': 'Failed to send email to reporter.'}), 500

    # Build CC copy for manager
    html_content_cc = f"""
    <html>
        <body>
            <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 30px 15px; margin: 0; min-height: 100%;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 25px; text-align: center; border-bottom: 3px solid #00f2fe;">
                        <h1 style="color: #ffffff; margin: 0; font-size: 1.5rem; letter-spacing: 1px; font-weight: 700;">COMMUNITY HERO</h1>
                    </div>
                    <div style="padding: 30px 25px; color: #334155; line-height: 1.6; font-size: 1rem;">
                        <p style="margin-top: 0;">Hello Manager <strong>{current_user.username}</strong>,</p>
                        <p>This is a confirmation copy of the message you securely sent to reporter <strong>{reporter.username}</strong> regarding issue: <strong style="color: #0f172a;">"{issue.title}"</strong>.</p>
                        
                        <div style="background-color: #f8fafc; border-left: 4px solid #cbd5e1; padding: 20px; border-radius: 6px; margin: 25px 0; border-top: 1px solid #f1f5f9; border-right: 1px solid #f1f5f9; border-bottom: 1px solid #f1f5f9; white-space: pre-wrap;">
                            <strong style="color: #0f172a; display: block; margin-bottom: 8px;">Subject: {subject}</strong>
                            {body}
                        </div>
                        
                        <p style="margin-bottom: 0; font-size: 0.9rem; color: #64748b;">* Note: A permanent record of this message has been archived in the secure log ledger. It can only be deleted by an Administrator.</p>
                    </div>
                    <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 0.8rem; color: #64748b; border-top: 1px solid #e2e8f0;">
                        <p style="margin: 0 0 5px 0; font-weight: 600;">Community Hero Manager Portal</p>
                        <p style="margin: 0;">This email is sent for reference and audit compliance.</p>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """

    # Send CC copy to manager
    send_brevo_email(
        to_email=current_user.email,
        to_name=current_user.username,
        subject=f"[Copy] Manager contact re: {issue.title} - {subject}",
        html_content=html_content_cc
    )

    # Log to sent_mails table
    log_record = SentMail(
        sender_id=current_user.id,
        receiver_id=reporter.id,
        issue_id=issue.id,
        subject=subject,
        body=body
    )
    db.session.add(log_record)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Message sent to reporter and copy CC\'d to your email.'})

@app.route('/api/admin/sent-mails', methods=['GET', 'DELETE'])
@login_required
def admin_sent_mails():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized. Admin only.'}), 403

    if request.method == 'GET':
        mails = SentMail.query.order_by(SentMail.sent_at.desc()).all()
        output = []
        for mail in mails:
            output.append({
                'id': mail.id,
                'sender': mail.sender.username,
                'sender_email': mail.sender.email,
                'receiver': mail.receiver.username,
                'receiver_email': mail.receiver.email,
                'issue_title': mail.issue.title,
                'issue_id': mail.issue_id,
                'subject': mail.subject,
                'body': mail.body,
                'sent_at': mail.sent_at.strftime('%Y-%m-%d %H:%M')
            })
        return jsonify(output)

    elif request.method == 'DELETE':
        mail_id = request.json.get('mail_id')
        if not mail_id:
            return jsonify({'error': 'Missing mail_id.'}), 400
        mail = SentMail.query.get_or_404(mail_id)
        db.session.delete(mail)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Mail log deleted successfully.'})

@app.route('/api/scheduler/check-reminders', methods=['POST', 'GET'])
def check_reminders():
    # Simple security token check
    auth_token = request.headers.get('Authorization') or request.args.get('token')
    expected_token = os.environ.get('SECRET_KEY')
    if not auth_token or auth_token != expected_token:
        return jsonify({'error': 'Unauthorized. Invalid or missing token.'}), 401

    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=7)
    
    all_issues = Issue.query.filter(Issue.status != 'Resolved', Issue.govt_status != 'DONE').all()
    
    flagged_by_district = {}
    
    for issue in all_issues:
        is_stale = issue.created_at < cutoff_date
        is_popular = issue.vote_score >= 10
        
        if is_stale or is_popular:
            key = (issue.state, issue.district)
            if key not in flagged_by_district:
                flagged_by_district[key] = []
            flagged_by_district[key].append((issue, is_stale, is_popular))

    emails_sent = 0
    for (state, district), issues_list in flagged_by_district.items():
        managers = User.query.filter_by(role='district_manager', state=state, district=district).all()
        if not managers:
            continue
            
        issues_html = ""
        for issue, is_stale, is_popular in issues_list:
            reasons = []
            if is_stale:
                reasons.append("Stale (>7 days unresolved)")
            if is_popular:
                reasons.append(f"High Vote Count (Score: {issue.vote_score})")
            reason_str = ", ".join(reasons)
            
            issues_html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 12px 10px; color: #0f172a;"><strong>#{issue.id} - {issue.title}</strong><br/><span style="color: #64748b; font-size: 0.8rem;">{issue.category}</span></td>
                <td style="padding: 12px 10px; color: #ef4444; font-weight: bold; font-size: 0.85rem;">{reason_str}</td>
                <td style="padding: 12px 10px; color: #64748b; font-size: 0.85rem; white-space: nowrap;">{issue.created_at.strftime('%Y-%m-%d')}</td>
            </tr>
            """
            
        subject = f"[Reminder] High Priority Issues in {district}, {state}"
        for manager in managers:
            html_content = f"""
            <html>
                <body>
                    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f8fafc; padding: 30px 15px; margin: 0; min-height: 100%;">
                        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);">
                            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 25px; text-align: center; border-bottom: 3px solid #ef4444;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 1.5rem; letter-spacing: 1px; font-weight: 700;">PRIORITY ISSUES DIGEST</h1>
                            </div>
                            <div style="padding: 30px 25px; color: #334155; line-height: 1.6; font-size: 1rem;">
                                <p style="margin-top: 0;">Hello Manager <strong>{manager.username}</strong>,</p>
                                <p>The following reported issues in your district <strong style="color: #0f172a;">{district}, {state}</strong> have reached a priority threshold and require immediate attention:</p>
                                
                                <div style="margin: 25px 0; overflow-x: auto;">
                                    <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.9rem;">
                                        <thead>
                                            <tr style="background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; color: #475569;">
                                                <th style="padding: 12px 10px; font-weight: 600;">Issue Info</th>
                                                <th style="padding: 12px 10px; font-weight: 600;">Priority Flag</th>
                                                <th style="padding: 12px 10px; font-weight: 600;">Reported Date</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {issues_html}
                                        </tbody>
                                    </table>
                                </div>
                                
                                <p style="margin-bottom: 0;">Please log into the <a href="{os.environ.get('WEB_LINK_GCP', '#')}" style="color: #00f2fe; text-decoration: underline; font-weight: 600;">Community Hero Management Dashboard</a> to inspect and update these reports.</p>
                            </div>
                            <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 0.8rem; color: #64748b; border-top: 1px solid #e2e8f0;">
                                <p style="margin: 0 0 5px 0; font-weight: 600;">Community Hero Escalation System</p>
                                <p style="margin: 0;">This operational digest is auto-generated based on issue resolution times and public vote thresholds.</p>
                            </div>
                        </div>
                    </div>
                </body>
            </html>
            """
            send_brevo_email(manager.email, manager.username, subject, html_content)
            emails_sent += 1

    return jsonify({'success': True, 'message': f'Reminder digest sent to {emails_sent} managers.'})


@app.route('/api/managers/state', methods=['POST'])
@login_required
def create_state_manager():
    if current_user.role != 'admin':
        flash('Unauthorized. Only Admin can create State Managers.', 'error')
        return redirect(url_for('dashboard'))
        
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    state = request.form.get('state')
    
    if not username or not email or not password or not state:
        flash('All fields are required.', 'error')
        return redirect(url_for('dashboard'))
        
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('dashboard'))
        
    user = User(
        username=username,
        email=email,
        role='state_manager',
        state=state,
        created_by_id=current_user.id
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    flash(f"Successfully created State Manager for {state}.", 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/managers/district', methods=['POST'])
@login_required
def create_district_manager():
    # Only state managers (or admin inspecting a state) can create district managers
    target_state = None
    if current_user.role == 'state_manager':
        target_state = current_user.state
    elif current_user.role == 'admin' and session.get('inspect_state'):
        target_state = session.get('inspect_state')
    else:
        flash('Unauthorized. Only State Managers can perform this action.', 'error')
        return redirect(url_for('dashboard'))
        
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    district = request.form.get('district')
    
    if not username or not email or not password or not district:
        flash('All fields are required.', 'error')
        return redirect(url_for('dashboard'))
        
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('dashboard'))
        
    lat, lon, _, _ = geocode_address(f"{district}, {target_state}")
    
    user = User(
        username=username,
        email=email,
        role='district_manager',
        state=target_state,
        district=district,
        latitude=lat,
        longitude=lon,
        created_by_id=current_user.id
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    flash(f"Successfully created District Manager for {district}, {target_state}.", 'success')
    return redirect(url_for('dashboard'))

@app.route('/api/issues/<int:issue_id>/update', methods=['POST'])
@login_required
def update_issue(issue_id):
    # Fallback/Citizen general logs update
    issue = Issue.query.get_or_404(issue_id)
    content = request.form.get('content')
    status_update = request.form.get('status')
    
    if not content or len(content.strip()) == 0:
        return jsonify({'error': 'Update status log description is required.'}), 400
        
    log = UpdateLog(
        issue_id=issue_id,
        user_id=current_user.id,
        content=content,
        status_update=status_update if status_update else None
    )
    db.session.add(log)
    
    # Change status of issue if provided (only allowed for general Open/Resolved updates by citizen)
    if status_update and status_update in ['Open', 'Under Review', 'In Progress', 'Resolved']:
        if current_user.role != 'citizen' and current_user.id != issue.user_id:
             return jsonify({'error': 'Unauthorized status update.'}), 403
        old_status = issue.status
        issue.status = status_update
        
        # Award points for resolving or updating issues
        if status_update == 'Resolved' and old_status != 'Resolved':
            issue.reporter.points += 50 # Reward the reporter!
            current_user.points += 25 # Reward the solver/verifier!
        else:
            current_user.points += 5 # General updates points
            
    db.session.commit()
    return jsonify({'success': True})

# --- DATABASE SETUP ---

def seed_database():
    """Seed DB with mock data for instant validation."""
    if User.query.first() is not None:
        return
        
    # Create Admin
    admin = User(username='admin', email='admin@communityhero.gov', role='admin')
    admin.set_password('password123')
    db.session.add(admin)
    db.session.commit()
    
    # Create State Managers
    sm_kar = User(username='state_mgr_karnataka', email='karnataka@communityhero.gov', role='state_manager', state='Karnataka', created_by_id=admin.id)
    sm_kar.set_password('password123')
    
    sm_mah = User(username='state_mgr_maharashtra', email='maharashtra@communityhero.gov', role='state_manager', state='Maharashtra', created_by_id=admin.id)
    sm_mah.set_password('password123')
    
    sm_del = User(username='state_mgr_delhi', email='delhi@communityhero.gov', role='state_manager', state='Delhi', created_by_id=admin.id)
    sm_del.set_password('password123')
    
    db.session.add_all([sm_kar, sm_mah, sm_del])
    db.session.commit()
    
    # Create District Managers
    dm_blr = User(username='dist_mgr_blr', email='bangalore@communityhero.gov', role='district_manager', state='Karnataka', district='Bangalore Urban', created_by_id=sm_kar.id)
    dm_blr.set_password('password123')
    
    dm_pune = User(username='dist_mgr_pune', email='pune@communityhero.gov', role='district_manager', state='Maharashtra', district='Pune', created_by_id=sm_mah.id)
    dm_pune.set_password('password123')
    
    dm_ndls = User(username='dist_mgr_ndls', email='newdelhi@communityhero.gov', role='district_manager', state='Delhi', district='New Delhi', created_by_id=sm_del.id)
    dm_ndls.set_password('password123')
    
    db.session.add_all([dm_blr, dm_pune, dm_ndls])
    db.session.commit()
    
    # Create Citizens
    u1 = User(
        username='citizen_alex', 
        email='alex@example.com', 
        points=120, 
        role='citizen',
        state='Karnataka',
        district='Bangalore Urban',
        address='MG Road, Bengaluru, Karnataka, India',
        latitude=12.9716,
        longitude=77.5946
    )
    u1.set_password('password123')
    
    u2 = User(
        username='jane_doe', 
        email='jane@example.com', 
        points=85, 
        role='citizen',
        state='Karnataka',
        district='Bangalore Urban',
        address='Indiranagar, Bengaluru, Karnataka, India',
        latitude=12.97189,
        longitude=77.64115
    )
    u2.set_password('password123')
 
    u3 = User(
        username='citizen_pune',
        email='pune_citizen@example.com',
        points=50,
        role='citizen',
        state='Maharashtra',
        district='Pune',
        address='FC Road, Pune, Maharashtra, India',
        latitude=18.5204,
        longitude=73.8567
    )
    u3.set_password('password123')
 
    u4 = User(
        username='citizen_delhi',
        email='delhi_citizen@example.com',
        points=60,
        role='citizen',
        state='Delhi',
        district='New Delhi',
        address='Connaught Place, New Delhi, Delhi, India',
        latitude=28.6139,
        longitude=77.2090
    )
    u4.set_password('password123')

    # Additional Citizens
    u5 = User(
        username='citizen_priya',
        email='priya@example.com',
        points=240,
        role='citizen',
        state='Karnataka',
        district='Bangalore Urban',
        address='Koramangala, Bengaluru, Karnataka, India',
        latitude=12.9352,
        longitude=77.6245
    )
    u5.set_password('password123')

    u6 = User(
        username='citizen_rahul',
        email='rahul@example.com',
        points=180,
        role='citizen',
        state='Maharashtra',
        district='Pune',
        address='Kothrud, Pune, Maharashtra, India',
        latitude=18.5074,
        longitude=73.8077
    )
    u6.set_password('password123')

    u7 = User(
        username='citizen_amit',
        email='amit@example.com',
        points=95,
        role='citizen',
        state='Delhi',
        district='New Delhi',
        address='Dwarka, New Delhi, Delhi, India',
        latitude=28.5804,
        longitude=77.0600
    )
    u7.set_password('password123')

    u8 = User(
        username='citizen_sunita',
        email='sunita@example.com',
        points=150,
        role='citizen',
        state='Karnataka',
        district='Bangalore Urban',
        address='Jayanagar, Bengaluru, Karnataka, India',
        latitude=12.9250,
        longitude=77.5890
    )
    u8.set_password('password123')

    u9 = User(
        username='citizen_vivek',
        email='vivek@example.com',
        points=310,
        role='citizen',
        state='Maharashtra',
        district='Pune',
        address='Viman Nagar, Pune, Maharashtra, India',
        latitude=18.5590,
        longitude=73.7925
    )
    u9.set_password('password123')

    u10 = User(
        username='citizen_ananya',
        email='ananya@example.com',
        points=40,
        role='citizen',
        state='Delhi',
        district='New Delhi',
        address='Saket, New Delhi, Delhi, India',
        latitude=28.5244,
        longitude=77.2100
    )
    u10.set_password('password123')
    
    db.session.add_all([u1, u2, u3, u4, u5, u6, u7, u8, u9, u10])
    db.session.commit()
    
    # Create issues
    i1 = Issue(
        title='Dangerous Deep Pothole on Main St.',
        description='A massive pothole has opened up near the crosswalk of Main St and 4th Ave. Multiple cars have hit it. Extremely dangerous for motorcyclists.',
        intensity='High',
        category='Roads',
        latitude=12.9715987,
        longitude=77.5945627,
        status='In Progress',
        govt_status='ONGOING',
        state='Karnataka',
        district='Bangalore Urban',
        user_id=u1.id,
        govt_status_updated_at=datetime.utcnow()
    )
    
    i2 = Issue(
        title='Streetlight out for a block on Elm Road',
        description='Three streetlights are completely out near the park, leaving the entire stretch dark. Residents feel unsafe walking home after sunset.',
        intensity='Medium',
        category='Streetlights',
        latitude=12.9725987,
        longitude=77.5965627,
        status='Open',
        govt_status='NOT VISITED',
        state='Karnataka',
        district='Bangalore Urban',
        user_id=u2.id
    )
    
    i3 = Issue(
        title='Illegal Garbage Dump near Community Park',
        description='People are dumping bags of household waste, broken furniture, and organic waste next to the park entrance. Stray animals are scattering it everywhere.',
        intensity='High',
        category='Waste Management',
        latitude=12.9705987,
        longitude=77.5925627,
        status='Open',
        govt_status='NOT VISITED',
        state='Karnataka',
        district='Bangalore Urban',
        user_id=u1.id
    )
 
    i4 = Issue(
        title='Water Supply Leakage on FC Road',
        description='Fresh municipal water is leaking from the underground main pipe on FC Road near Starbucks. Wasting thousands of liters daily.',
        intensity='High',
        category='Water & Sewerage',
        latitude=18.5204,
        longitude=73.8567,
        status='In Progress',
        govt_status='ONGOING',
        state='Maharashtra',
        district='Pune',
        user_id=u3.id,
        govt_status_updated_at=datetime.utcnow()
    )
 
    i5 = Issue(
        title='Broken Streetlight near Connaught Place',
        description='Inner circle block A streetlights have been completely dark for 3 days. Creates safety hazard for shoppers.',
        intensity='Medium',
        category='Streetlights',
        latitude=28.6139,
        longitude=77.2090,
        status='Open',
        govt_status='NOT VISITED',
        state='Delhi',
        district='New Delhi',
        user_id=u4.id
    )
 
    i6 = Issue(
        title='Public Park Overgrown and Trash Accumulation',
        description='The public park near FC Road has overgrown weeds and there is a lot of plastic litter scattered around the walking path.',
        intensity='Low',
        category='Parks & Recreation',
        latitude=18.5224,
        longitude=73.8587,
        status='Open',
        govt_status='NOT VISITED',
        state='Maharashtra',
        district='Pune',
        user_id=u3.id
    )
 
    i7 = Issue(
        title='Overflowing Drainage near CP',
        description='There is an overflowing sewage manhole near block B of Connaught Place, causing a terrible smell and pedestrian blockages.',
        intensity='High',
        category='Water & Sewerage',
        latitude=28.6149,
        longitude=77.2110,
        status='Open',
        govt_status='NOT VISITED',
        state='Delhi',
        district='New Delhi',
        user_id=u4.id
    )
 
    i8 = Issue(
        title='Damaged Traffic Signal on 100 Feet Rd',
        description='The pedestrian crossing signal is damaged and flashing red constantly, causing confusion and near-misses.',
        intensity='Medium',
        category='Traffic & Signage',
        latitude=12.9735,
        longitude=77.6425,
        status='Open',
        govt_status='NOT VISITED',
        state='Karnataka',
        district='Bangalore Urban',
        user_id=u2.id
    )
 
    i9 = Issue(
        title='Illegal Commercial Dumping',
        description='A local restaurant is dumping waste bins directly on the footpath behind MG Road every evening.',
        intensity='High',
        category='Waste Management',
        latitude=12.9720,
        longitude=77.5955,
        status='Open',
        govt_status='NOT VISITED',
        state='Karnataka',
        district='Bangalore Urban',
        user_id=u1.id
    )

    # NEW DETAILED ISSUES
    i10 = Issue(
        title='Water Pipeline Burst in Koramangala',
        description='A major municipal water pipe has burst under the main road in Block 3 Koramangala. Water is shooting up to 10 feet in the air and flooding local shops.',
        intensity='High',
        category='Water & Sewerage',
        latitude=12.9345,
        longitude=77.6260,
        status='Resolved',
        govt_status='RESOLVED',
        state='Karnataka',
        district='Bangalore Urban',
        user_id=u5.id,
        govt_status_updated_at=datetime.utcnow()
    )

    i11 = Issue(
        title='Broken Footpath Tiles in Jayanagar 4th Block',
        description='Dozens of walking tiles are cracked or missing completely on the main boulevard. Multiple senior citizens have tripped and fallen here.',
        intensity='Medium',
        category='Roads',
        latitude=12.9262,
        longitude=77.5910,
        status='In Progress',
        govt_status='UNDER INVESTIGATION',
        state='Karnataka',
        district='Bangalore Urban',
        user_id=u8.id,
        govt_status_updated_at=datetime.utcnow()
    )

    i12 = Issue(
        title='Dangerous Open Manhole on Sarjapur Road',
        description='An open sewer manhole has been left completely uncovered on the busy Sarjapur Road junction. No safety signs or cones are placed.',
        intensity='High',
        category='Water & Sewerage',
        latitude=12.9160,
        longitude=77.6615,
        status='Open',
        govt_status='NOT VISITED',
        state='Karnataka',
        district='Bangalore Urban',
        user_id=u5.id
    )

    i13 = Issue(
        title='Overgrown Trees Blocking Traffic Lights',
        description='Lush branches are completely covering the traffic signal at Koramangala 80 Feet Road junction, causing major transit confusion.',
        intensity='Low',
        category='Traffic & Signage',
        latitude=12.9290,
        longitude=77.6210,
        status='Resolved',
        govt_status='RESOLVED',
        state='Karnataka',
        district='Bangalore Urban',
        user_id=u8.id,
        govt_status_updated_at=datetime.utcnow()
    )

    i14 = Issue(
        title='Missing Stormwater Manhole Cover in Kothrud',
        description='A deep stormwater drain has been left uncovered on a dark street corner in Kothrud, Pune. Highly dangerous for children playing nearby.',
        intensity='High',
        category='Water & Sewerage',
        latitude=18.5080,
        longitude=73.8090,
        status='Open',
        govt_status='NOT VISITED',
        state='Maharashtra',
        district='Pune',
        user_id=u6.id
    )

    i15 = Issue(
        title='Completely Dark Stretch on Baner Road',
        description='Five consecutive streetlights have failed near the highway bypass on Baner Road. The road is completely pitch black at night.',
        intensity='Medium',
        category='Streetlights',
        latitude=18.5605,
        longitude=73.7910,
        status='Resolved',
        govt_status='RESOLVED',
        state='Maharashtra',
        district='Pune',
        user_id=u9.id,
        govt_status_updated_at=datetime.utcnow()
    )

    i16 = Issue(
        title='Illegal Flex Banners Blocking Pedestrian Crossings',
        description='Large political banner frames have been erected directly blocking the sightlines of pedestrian crossings near Pune University.',
        intensity='Low',
        category='Traffic & Signage',
        latitude=18.5290,
        longitude=73.8420,
        status='Open',
        govt_status='UNDER INVESTIGATION',
        state='Maharashtra',
        district='Pune',
        user_id=u6.id
    )

    i17 = Issue(
        title='Uncollected Commercial Garbage Accumulation near River',
        description='Tons of plastic waste and food containers have been dumped along the Mutha river bed near Deccan. Foul stench spreading.',
        intensity='High',
        category='Waste Management',
        latitude=18.5150,
        longitude=73.8320,
        status='In Progress',
        govt_status='ONGOING',
        state='Maharashtra',
        district='Pune',
        user_id=u9.id,
        govt_status_updated_at=datetime.utcnow()
    )

    i18 = Issue(
        title='Deep Potholes on Ring Road near Lajpat Nagar',
        description='Multiple massive craters have developed on the busy Ring Road bridge, causing severe traffic jams and vehicle damage.',
        intensity='High',
        category='Roads',
        latitude=28.5675,
        longitude=77.2440,
        status='Resolved',
        govt_status='RESOLVED',
        state='Delhi',
        district='New Delhi',
        user_id=u7.id,
        govt_status_updated_at=datetime.utcnow()
    )

    i19 = Issue(
        title='Severe Water Logging near Dwarka Sector 10 Metro',
        description='Even after minor rain, the entire access road to Dwarka Sector 10 Metro station gets flooded with ankle-deep sewage water.',
        intensity='High',
        category='Water & Sewerage',
        latitude=28.5815,
        longitude=77.0610,
        status='In Progress',
        govt_status='ONGOING',
        state='Delhi',
        district='New Delhi',
        user_id=u7.id,
        govt_status_updated_at=datetime.utcnow()
    )

    i20 = Issue(
        title='Broken Benches and Overgrown Walkways in Lodhi Park',
        description='Several concrete benches are cracked or toppled, and walking paths are covered with thorns and dry bushes.',
        intensity='Low',
        category='Parks & Recreation',
        latitude=28.5910,
        longitude=77.2210,
        status='Open',
        govt_status='NOT VISITED',
        state='Delhi',
        district='New Delhi',
        user_id=u10.id
    )
    
    db.session.add_all([
        i1, i2, i3, i4, i5, i6, i7, i8, i9, 
        i10, i11, i12, i13, i14, i15, i16, i17, i18, i19, i20
    ])
    db.session.commit()
    
    # Add votes
    votes = [
        # i1 votes
        Vote(issue_id=i1.id, user_id=u2.id, vote_type='upvote'),
        Vote(issue_id=i1.id, user_id=u5.id, vote_type='upvote'),
        Vote(issue_id=i1.id, user_id=u8.id, vote_type='upvote'),
        # i12 open manhole (needs high score)
        Vote(issue_id=i12.id, user_id=u1.id, vote_type='upvote'),
        Vote(issue_id=i12.id, user_id=u2.id, vote_type='upvote'),
        Vote(issue_id=i12.id, user_id=u3.id, vote_type='upvote'),
        Vote(issue_id=i12.id, user_id=u4.id, vote_type='upvote'),
        Vote(issue_id=i12.id, user_id=u8.id, vote_type='upvote'),
        Vote(issue_id=i12.id, user_id=u9.id, vote_type='upvote'),
        Vote(issue_id=i12.id, user_id=u10.id, vote_type='upvote'),
        # i10 resolved votes
        Vote(issue_id=i10.id, user_id=u1.id, vote_type='upvote'),
        Vote(issue_id=i10.id, user_id=u8.id, vote_type='upvote'),
        # i4 votes
        Vote(issue_id=i4.id, user_id=u9.id, vote_type='upvote'),
        Vote(issue_id=i4.id, user_id=u6.id, vote_type='upvote'),
        # i14 votes
        Vote(issue_id=i14.id, user_id=u3.id, vote_type='upvote'),
        Vote(issue_id=i14.id, user_id=u9.id, vote_type='upvote'),
        # i17 votes
        Vote(issue_id=i17.id, user_id=u6.id, vote_type='upvote'),
        # i19 votes
        Vote(issue_id=i19.id, user_id=u10.id, vote_type='upvote'),
        Vote(issue_id=i19.id, user_id=u4.id, vote_type='upvote')
    ]
    db.session.add_all(votes)
    
    # Add comments
    comments = [
        Comment(issue_id=i1.id, user_id=u2.id, content="Agreed! Almost popped my tire here yesterday."),
        Comment(issue_id=i1.id, user_id=u5.id, content="This is on my daily route. Truly dangerous at night."),
        Comment(issue_id=i12.id, user_id=u1.id, content="Oh wow, this is a death trap. I hope the district manager acts fast."),
        Comment(issue_id=i12.id, user_id=u8.id, content="I put some branches inside to warn motorists, but we need a cover!"),
        Comment(issue_id=i10.id, user_id=u8.id, content="Thanks for the lightning fast resolution! Clean water is no longer flooding the pavement."),
        Comment(issue_id=i14.id, user_id=u9.id, content="Very risky, especially with monsoons starting soon."),
        Comment(issue_id=i17.id, user_id=u3.id, content="The municipal bins nearby are completely broken. People have no choice."),
        Comment(issue_id=i19.id, user_id=u4.id, content="Every single monsoon this road becomes a river. Terrible city drainage design!")
    ]
    db.session.add_all(comments)
    
    # Add UpdateLogs (user issue progress logs)
    logs = [
        # i1 logs
        UpdateLog(issue_id=i1.id, user_id=u1.id, content="Issue reported to the community.", status_update="Open"),
        UpdateLog(issue_id=i1.id, user_id=dm_blr.id, content="Government status updated to ONGOING. Patch team scheduled.", status_update="In Progress"),
        # i10 resolved pipeline logs
        UpdateLog(issue_id=i10.id, user_id=u5.id, content="Water pipeline burst reported.", status_update="Open"),
        UpdateLog(issue_id=i10.id, user_id=dm_blr.id, content="Water division team sent to location to investigate.", status_update="Under Review"),
        UpdateLog(issue_id=i10.id, user_id=dm_blr.id, content="Main line valve closed. Welding team repairing the burst pipe.", status_update="In Progress"),
        UpdateLog(issue_id=i10.id, user_id=dm_blr.id, content="Pipe welded successfully. Pavement cleaned up and road opened.", status_update="Resolved"),
        # i11 logs
        UpdateLog(issue_id=i11.id, user_id=u8.id, content="Footpath tiles issue reported.", status_update="Open"),
        UpdateLog(issue_id=i11.id, user_id=dm_blr.id, content="Investigating department assessing repair costs.", status_update="Under Review"),
        # i12 logs
        UpdateLog(issue_id=i12.id, user_id=u5.id, content="Open manhole reported on main transit lane.", status_update="Open"),
        # i14 logs
        UpdateLog(issue_id=i14.id, user_id=u6.id, content="Stormwater open drain reported.", status_update="Open"),
        # i15 logs
        UpdateLog(issue_id=i15.id, user_id=u9.id, content="Baner Road dark stretch reported.", status_update="Open"),
        UpdateLog(issue_id=i15.id, user_id=dm_pune.id, content="Electricity board replaced blown transformer fuse. All lights functioning.", status_update="Resolved"),
        # i17 logs
        UpdateLog(issue_id=i17.id, user_id=u9.id, content="River bank dump reported.", status_update="Open"),
        UpdateLog(issue_id=i17.id, user_id=dm_pune.id, content="Solid waste management division scheduled clean-up drive.", status_update="In Progress"),
        # i18 logs
        UpdateLog(issue_id=i18.id, user_id=u7.id, content="Ring road bridge craters reported.", status_update="Open"),
        UpdateLog(issue_id=i18.id, user_id=dm_ndls.id, content="Cold mix asphalt laid. Road surface restored completely.", status_update="Resolved"),
        # i19 logs
        UpdateLog(issue_id=i19.id, user_id=u7.id, content="Dwarka Metro water logging reported.", status_update="Open"),
        UpdateLog(issue_id=i19.id, user_id=dm_ndls.id, content="Suction pump deployed to drain excess water. Long term drain overhaul scheduled.", status_update="In Progress")
    ]
    db.session.add_all(logs)
    db.session.commit()

@app.cli.command("init-db")
def init_db():
    db.create_all()
    seed_database()
    print("Database initialized and seeded.")

# Initialize database and seed if empty on application import (works on Render free tier without shell access)
if not os.environ.get('TESTING'):
    with app.app_context():
        try:
            # Schema verification check and new seed data detection
            User.query.filter(User.district == 'test').first()
            SentMail.query.first()
            # Force recreate if our new seeded citizen 'citizen_priya' is missing to ensure database gets refreshed
            if not User.query.filter_by(username='citizen_priya').first():
                raise Exception("Outdated seed data detected. Refreshing database.")
        except Exception:
            db.session.rollback()
            db.drop_all()
        db.create_all()
        seed_database()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

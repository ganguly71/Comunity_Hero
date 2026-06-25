import os
import math
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import db, User, Issue, Comment, Vote, UpdateLog
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
                            address.get('state_district') or address.get('city') or 'Bangalore Urban')
                state = address.get('state') or 'Karnataka'
                return lat, lon, district, state
    except Exception as e:
        print(f"Forward Geocoding error: {e}")
    # Fallback to Bangalore defaults
    return 12.9716, 77.5946, "Bangalore Urban", "Karnataka"

def reverse_geocode(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1"
        headers = {'User-Agent': 'CommunityHero/1.0 (contact@example.com)'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            address = data.get('address', {})
            district = (address.get('county') or address.get('city_district') or 
                        address.get('state_district') or address.get('city') or 'Bangalore Urban')
            state = address.get('state') or 'Karnataka'
            return district, state
    except Exception as e:
        print(f"Reverse Geocoding error: {e}")
    return "Bangalore Urban", "Karnataka"

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
        address = request.form.get('address')
        
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
            state_managers = User.query.filter_by(role='state_manager').all()
            return render_template('dashboard.html', 
                                   states_data=states_data, 
                                   state_managers=state_managers)
                                   
    else: # Citizen
        user_issues = Issue.query.filter_by(user_id=current_user.id).order_by(Issue.created_at.desc()).all()
        return render_template('dashboard.html', issues=user_issues)

@app.route('/leaderboard')
@login_required
def leaderboard():
    # 1. Top citizens
    users = User.query.filter_by(role='citizen').order_by(User.points.desc()).limit(10).all()
    
    # 2. State Districts Performance Leaderboard
    state_query = current_user.state or 'Karnataka'
    all_state_issues = Issue.query.filter_by(state=state_query).all()
    district_totals = {}
    district_completed = {}
    for issue in all_state_issues:
        d = issue.district or 'Unknown'
        district_totals[d] = district_totals.get(d, 0) + 1
        if issue.govt_status == 'DONE':
            district_completed[d] = district_completed.get(d, 0) + 1
            
    # Also fetch district managers to include districts that might have no issues reported yet
    managers_dist = db.session.query(User.district).filter_by(state=state_query, role='district_manager').distinct().all()
    for row in managers_dist:
        if row[0] and row[0] not in district_totals:
            district_totals[row[0]] = 0
            
    district_standings = []
    for d, total in district_totals.items():
        completed = district_completed.get(d, 0)
        rate = (completed / total * 100) if total > 0 else 0
        district_standings.append({
            'district': d,
            'total': total,
            'completed': completed,
            'rate': round(rate, 1)
        })
    district_standings.sort(key=lambda x: x['rate'], reverse=True)
    
    # 3. Inter-State Leaderboard
    all_issues = Issue.query.all()
    state_totals = {}
    state_completed = {}
    for issue in all_issues:
        s = issue.state or 'Unknown'
        state_totals[s] = state_totals.get(s, 0) + 1
        if issue.govt_status == 'DONE':
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
                           selected_state=state_query)

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

    # Range Check: Must be within 10 km of address OR current GPS location
    dist_to_address = haversine_distance(latitude, longitude, current_user.latitude, current_user.longitude)
    dist_to_gps = haversine_distance(latitude, longitude, user_lat, user_lng) if (user_lat is not None) else float('inf')
    
    if dist_to_address > 10.0 and dist_to_gps > 10.0:
        return jsonify({'error': 'Cannot report an issue located more than 10 KM away from your home address or current location.'}), 400

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
    if issue_district == "Unknown District" or issue_state == "Unknown State":
        issue_district = current_user.district or "Unknown District"
        issue_state = current_user.state or "Unknown State"

    if current_user.role == 'citizen':
        if issue_district != current_user.district or issue_state != current_user.state:
            return jsonify({'error': f"Cannot report issues outside your registered area ({current_user.district}, {current_user.state})."}), 403

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
    
    return jsonify({
        'success': True,
        'message': f'Issue reported! Assigned to {issue_district}, {issue_state}. Auto-categorized: {category}. +15 Pts!',
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
            if vote_type == 'upvote':
                reporter.points = max(0, reporter.points - 5)
            else:
                reporter.points += 2
            db.session.commit()
            return jsonify({'success': True, 'action': 'retracted', 'score': issue.vote_score})
        else:
            # Switch vote
            existing_vote.vote_type = vote_type
            if vote_type == 'upvote':
                reporter.points += 7
            else:
                reporter.points = max(0, reporter.points - 7)
            db.session.commit()
            return jsonify({'success': True, 'action': 'switched', 'score': issue.vote_score})
    else:
        # New vote
        new_vote = Vote(issue_id=issue_id, user_id=current_user.id, vote_type=vote_type)
        db.session.add(new_vote)
        if vote_type == 'upvote':
            reporter.points += 5
        else:
            reporter.points = max(0, reporter.points - 2)
            
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
        
    user = User(
        username=username,
        email=email,
        role='district_manager',
        state=target_state,
        district=district,
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
    
    db.session.add_all([u1, u2, u3, u4])
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
    
    db.session.add_all([i1, i2, i3, i4, i5, i6, i7, i8, i9])
    db.session.commit()
    
    # Add comments and logs
    v1 = Vote(issue_id=i1.id, user_id=u2.id, vote_type='upvote')
    c1 = Comment(issue_id=i1.id, user_id=u2.id, content="Agreed! Almost popped my tire here yesterday.")
    log1 = UpdateLog(issue_id=i1.id, user_id=u1.id, content="Issue reported to the community.", status_update="Open")
    log2 = UpdateLog(issue_id=i1.id, user_id=dm_blr.id, content="Government status updated to ONGOING. Patch team scheduled.", status_update="ONGOING")
    
    db.session.add_all([v1, c1, log1, log2])
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
            # Schema verification check
            User.query.filter(User.district == 'test').first()
        except Exception:
            db.session.rollback()
            db.drop_all()
        db.create_all()
        seed_database()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

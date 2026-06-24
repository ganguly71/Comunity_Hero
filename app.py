import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import db, User, Issue, Comment, Vote, UpdateLog
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from supabase import create_client, Client

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
@login_required
def index():
    return render_template('index.html')

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
        role = request.form.get('role', 'citizen')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')
            
        user = User(username=username, email=email, role=role, points=50) # give registration points
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('index'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_issues = Issue.query.filter_by(user_id=current_user.id).order_by(Issue.created_at.desc()).all()
    return render_template('dashboard.html', issues=user_issues)

@app.route('/leaderboard')
@login_required
def leaderboard():
    users = User.query.order_by(User.points.desc()).limit(10).all()
    return render_template('leaderboard.html', users=users)

@app.route('/stats')
@login_required
def stats():
    total_issues = Issue.query.count()
    resolved_issues = Issue.query.filter_by(status='Resolved').count()
    open_issues = Issue.query.filter(Issue.status != 'Resolved').count()
    
    # Category statistics
    categories = ['Roads', 'Water & Sewerage', 'Waste Management', 'Streetlights', 'Utilities', 'Other']
    cat_counts = {}
    for cat in categories:
        cat_counts[cat] = Issue.query.filter_by(category=cat).count()
        
    return render_template('stats.html', 
                           total_issues=total_issues,
                           resolved_issues=resolved_issues,
                           open_issues=open_issues,
                           cat_counts=cat_counts)

# --- API ENDPOINTS ---

@app.route('/api/issues', methods=['GET'])
@login_required
def get_issues():
    issues = Issue.query.order_by(Issue.created_at.desc()).all()
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
            'created_at': issue.created_at.strftime('%Y-%m-%d %H:%M'),
            'reporter': issue.reporter.username,
            'reporter_points': issue.reporter.points,
            'score': issue.vote_score,
            'user_vote': voted,
            'comments': comments_list,
            'logs': logs_list
        })
    return jsonify(output)

@app.route('/api/issues/report', methods=['POST'])
@login_required
def report_issue():
    title = request.form.get('title')
    description = request.form.get('description')
    intensity = request.form.get('intensity', 'Medium')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    
    if not title or not description or not latitude or not longitude:
        return jsonify({'error': 'Missing required fields'}), 400
        
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except ValueError:
        return jsonify({'error': 'Invalid coordinates'}), 400

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

    issue = Issue(
        title=title,
        description=description,
        intensity=intensity,
        category=category,
        latitude=latitude,
        longitude=longitude,
        image_filename=image_filename,
        status='Open',
        user_id=current_user.id
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
        'message': f'Issue reported! Auto-categorized as: {category}. You earned 15 points!',
        'issue_id': issue.id,
        'category': category
    })

@app.route('/api/issues/<int:issue_id>/vote', methods=['POST'])
@login_required
def vote_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
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

@app.route('/api/issues/<int:issue_id>/update', methods=['POST'])
@login_required
def update_issue(issue_id):
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
    
    # Change status of issue if provided
    if status_update and status_update in ['Open', 'Under Review', 'In Progress', 'Resolved']:
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
        
    # Create users
    u1 = User(username='alex_green', email='alex@example.com', points=120, role='citizen')
    u1.set_password('password123')
    u2 = User(username='jane_doe', email='jane@example.com', points=85, role='citizen')
    u2.set_password('password123')
    u3 = User(username='city_officer_sam', email='sam@city.gov', points=210, role='authority')
    u3.set_password('password123')
    
    db.session.add_all([u1, u2, u3])
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
        user_id=u1.id
    )
    
    i2 = Issue(
        title='Streetlight out for a block on Elm Road',
        description='Three streetlights are completely out near the park, leaving the entire stretch dark. Residents feel unsafe walking home after sunset.',
        intensity='Medium',
        category='Streetlights',
        latitude=12.9725987,
        longitude=77.5965627,
        status='Open',
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
        user_id=u1.id
    )
    
    db.session.add_all([i1, i2, i3])
    db.session.commit()
    
    # Add comments and logs
    v1 = Vote(issue_id=i1.id, user_id=u2.id, vote_type='upvote')
    c1 = Comment(issue_id=i1.id, user_id=u2.id, content="Agreed! Almost popped my tire here yesterday.")
    log1 = UpdateLog(issue_id=i1.id, user_id=u1.id, content="Issue reported to the community.", status_update="Open")
    log2 = UpdateLog(issue_id=i1.id, user_id=u3.id, content="City maintenance team scheduled to patch this tomorrow.", status_update="In Progress")
    
    db.session.add_all([v1, c1, log1, log2])
    db.session.commit()

@app.cli.command("init-db")
def init_db():
    db.create_all()
    seed_database()
    print("Database initialized and seeded.")

# Initialize database and seed if empty on application import (works on Render free tier without shell access)
with app.app_context():
    db.create_all()
    seed_database()

if __name__ == '__main__':
    app.run(debug=True, port=5000)

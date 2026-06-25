from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    points = db.Column(db.Integer, default=0)
    role = db.Column(db.String(20), default='citizen') # 'citizen', 'district_manager', 'state_manager', 'admin'
    state = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    email_updated_at = db.Column(db.DateTime, nullable=True)
    address_updated_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    issues = db.relationship('Issue', backref='reporter', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    votes = db.relationship('Vote', backref='voter', lazy=True)
    update_logs = db.relationship('UpdateLog', backref='logger', lazy=True)
    created_users = db.relationship('User', backref=db.backref('creator', remote_side=[id]), lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Issue(db.Model):
    __tablename__ = 'issues'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    intensity = db.Column(db.String(20), default='Medium') # 'Low', 'Medium', 'High'
    category = db.Column(db.String(50), nullable=False) # 'Roads', 'Water', 'Waste', 'Streetlights', 'Other'
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='Open') # 'Open', 'Under Review', 'In Progress', 'Resolved'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    state = db.Column(db.String(100), nullable=True)
    district = db.Column(db.String(100), nullable=True)
    govt_status = db.Column(db.String(50), default='NOT VISITED') # 'NOT VISITED', 'ONGOING', 'DONE'
    govt_status_updated_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    comments = db.relationship('Comment', backref='issue', lazy=True, cascade="all, delete-orphan")
    votes = db.relationship('Vote', backref='issue', lazy=True, cascade="all, delete-orphan")
    update_logs = db.relationship('UpdateLog', backref='issue', lazy=True, cascade="all, delete-orphan")

    @property
    def vote_score(self):
        upvotes = sum(1 for v in self.votes if v.vote_type == 'upvote')
        downvotes = sum(1 for v in self.votes if v.vote_type == 'downvote')
        return upvotes - downvotes

class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Vote(db.Model):
    __tablename__ = 'votes'
    
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vote_type = db.Column(db.String(10), nullable=False) # 'upvote' or 'downvote'
    
    __table_args__ = (db.UniqueConstraint('issue_id', 'user_id', name='unique_user_issue_vote'),)

class UpdateLog(db.Model):
    __tablename__ = 'update_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status_update = db.Column(db.String(20), nullable=True) # New status if changed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SentMail(db.Model):
    __tablename__ = 'sent_mails'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    issue_id = db.Column(db.Integer, db.ForeignKey('issues.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')
    issue = db.relationship('Issue', backref='contact_emails')


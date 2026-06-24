import os
from dotenv import load_dotenv
load_dotenv()

from app import app, db, User, Issue

with app.app_context():
    print("--- Database inspection ---")
    try:
        users = User.query.all()
        print(f"Total users found: {len(users)}")
        for u in users:
            print(f"- Username: {u.username}, Role: {u.role}, Email: {u.email}, State: {u.state}, District: {u.district}")
            
        issues = Issue.query.all()
        print(f"Total issues found: {len(issues)}")
        for i in issues:
            print(f"- Issue ID: {i.id}, Title: {i.title}, District: {i.district}, State: {i.state}, Govt Status: {i.govt_status}")
    except Exception as e:
        print(f"Error querying database: {e}")

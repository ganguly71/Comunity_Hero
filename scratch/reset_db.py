import os
from dotenv import load_dotenv
load_dotenv()

from app import app, db, seed_database

with app.app_context():
    print("Dropping all tables on live database...")
    db.drop_all()
    print("Creating all tables...")
    db.create_all()
    print("Seeding database with proper demo users...")
    seed_database()
    print("Database reset and seeded successfully!")

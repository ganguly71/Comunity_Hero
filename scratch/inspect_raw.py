import os
import psycopg2
from dotenv import load_dotenv
load_dotenv()

db_url = os.environ.get('DATABASE_URL')
if db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

print("Connecting to:", db_url)
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public';")
    print("Tables:", cur.fetchall())
    
    cur.execute("SELECT id, username, role, email FROM users;")
    print("Users in database:")
    for row in cur.fetchall():
        print(row)
    conn.close()
except Exception as e:
    print("Error:", e)

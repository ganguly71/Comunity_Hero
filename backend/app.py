import os
import math
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Environment variables
DB_URL = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# Configure Gemini API if key is present
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# ==========================================
# IN-MEMORY DATABASE FALLBACK (For zero-config local runs)
# ==========================================
mock_db = {
    "wards": [
        {"id": "w1", "name": "Indiranagar", "city": "Bengaluru"},
        {"id": "w2", "name": "Koramangala", "city": "Bengaluru"},
        {"id": "w3", "name": "HSR Layout", "city": "Bengaluru"},
        {"id": "w4", "name": "Whitefield", "city": "Bengaluru"}
    ],
    "badges": [
        {"id": "b1", "name": "First Reporter", "icon": "🏅", "description": "Submit your first report", "xpReward": 50, "conditionType": "reports_count", "conditionValue": 1},
        {"id": "b2", "name": "Neighborhood Watch", "icon": "👁️", "description": "Verify 5 issues reported by others", "xpReward": 100, "conditionType": "verified_count", "conditionValue": 5},
        {"id": "b3", "name": "Problem Solver", "icon": "🛠️", "description": "Have 3 of your reported issues successfully resolved", "xpReward": 150, "conditionType": "resolved_count", "conditionValue": 3},
        {"id": "b4", "name": "Ward Champion", "icon": "👑", "description": "Submit 10 reports in a single month", "xpReward": 200, "conditionType": "reports_count", "conditionValue": 10}
    ],
    "users": [
        {"id": "u1", "email": "aditya@communityhero.in", "fullName": "Aditya Kumar", "phone": "+91 98765 43210", "avatarUrl": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&h=150", "role": "citizen", "wardId": "w1", "xpPoints": 120, "badgeIds": ["b1"], "reportsCount": 3, "verifiedCount": 4},
        {"id": "u2", "email": "priya@communityhero.in", "fullName": "Priya Sharma", "phone": "+91 98123 45678", "avatarUrl": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=150&h=150", "role": "citizen", "wardId": "w2", "xpPoints": 240, "badgeIds": ["b1", "b2"], "reportsCount": 8, "verifiedCount": 12},
        {"id": "u3", "email": "rohan.mod@communityhero.in", "fullName": "Rohan Sen", "phone": "+91 99000 88888", "avatarUrl": "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=150&h=150", "role": "moderator", "wardId": "w3", "xpPoints": 350, "badgeIds": ["b1", "b2", "b3"], "reportsCount": 12, "verifiedCount": 45},
        {"id": "u4", "email": "officer.ramesh@bbmp.gov.in", "fullName": "Officer Ramesh Gowda", "phone": "+91 98888 77777", "avatarUrl": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&h=150", "role": "authority", "wardId": "w1", "xpPoints": 0, "badgeIds": [], "reportsCount": 0, "verifiedCount": 0},
        {"id": "u5", "email": "admin@communityhero.in", "fullName": "Super Admin", "phone": "+91 90000 00000", "avatarUrl": "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=150&h=150", "role": "admin", "wardId": "w3", "xpPoints": 10, "badgeIds": [], "reportsCount": 0, "verifiedCount": 0}
    ],
    "issues": [
        {
            "id": "iss1",
            "title": "Deep Pothole on Indiranagar 100ft Road",
            "description": "Huge pothole right in the middle of the road near the corner turn. Causes vehicles to swerve dangerously, especially two-wheelers at night.",
            "category": "pothole",
            "severity": "critical",
            "status": "verified",
            "mediaUrls": ["https://images.unsplash.com/photo-1515162305285-0293e4767cc2?auto=format&fit=crop&w=800&q=80"],
            "latitude": 12.9784,
            "longitude": 77.6408,
            "addressText": "Indiranagar 100 Feet Rd, Hal 2nd Stage, Indiranagar, Bengaluru, Karnataka 560038",
            "wardId": "w1",
            "reporterId": "u2",
            "assignedTo": None,
            "aiCategory": "pothole",
            "aiConfidence": 0.96,
            "upvoteCount": 15,
            "isDuplicate": False,
            "duplicateOf": None,
            "createdAt": "2026-06-22T08:30:00Z",
            "updatedAt": "2026-06-22T10:15:00Z",
            "resolvedAt": None
        },
        {
            "id": "iss2",
            "title": "Broken Streetlight Near Metro Station",
            "description": "The streetlight has been flicking for a week and has now completely died. The alley is pitch dark and unsafe for commuters walking home late.",
            "category": "streetlight",
            "severity": "high",
            "status": "in_progress",
            "mediaUrls": ["https://images.unsplash.com/photo-1509024644558-2f56ce76c490?auto=format&fit=crop&w=800&q=80"],
            "latitude": 12.9722,
            "longitude": 77.6320,
            "addressText": "Chinmaya Mission Hospital Rd, Indiranagar, Bengaluru, Karnataka 560038",
            "wardId": "w1",
            "reporterId": "u1",
            "assignedTo": "u4",
            "aiCategory": "streetlight",
            "aiConfidence": 0.98,
            "upvoteCount": 7,
            "isDuplicate": False,
            "duplicateOf": None,
            "createdAt": "2026-06-20T21:00:00Z",
            "updatedAt": "2026-06-23T11:00:00Z",
            "resolvedAt": None
        }
    ],
    "verifications": [
        {"id": "v1", "issueId": "iss1", "userId": "u1", "type": "upvote", "createdAt": "2026-06-22T09:00:00Z"}
    ],
    "comments": [
        {"id": "c1", "issueId": "iss1", "userId": "u1", "content": "I almost fell here on my scooter yesterday.", "isAuthority": False, "createdAt": "2026-06-22T09:05:00Z"}
    ],
    "statusHistory": [
        {"id": "sh1", "issueId": "iss1", "changedBy": "u2", "oldStatus": None, "newStatus": "reported", "note": "Initial submission", "createdAt": "2026-06-22T08:30:00Z"}
    ]
}

# ==========================================
# DATABASE HELPER METHODS
# ==========================================
def get_db_connection():
    if not DB_URL:
        return None
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"Error connecting to real DB: {e}")
        return None

# ==========================================
# AI CLASSIFICATION (GEMINI / KEYWORD FALLBACK)
# ==========================================
def run_ai_analysis(description):
    desc_lower = (description or "").lower()
    
    # Try calling real Gemini if key is active
    if GEMINI_KEY:
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"""
            Analyze this community complaint text: "{description}"
            Classify it into exactly one of these categories: pothole, water_leak, streetlight, waste, road_damage, other.
            Suggest a severity score: low, medium, high, critical.
            Provide a short list of 2-3 tags.
            Provide a suggested title (max 5 words).
            Respond with JSON using keys: category, severity, tags, suggestedTitle, confidence (float 0.0 to 1.0).
            Ensure response is purely JSON.
            """
            response = model.generate_content(prompt)
            # Simple JSON parse helper (strip code block markup if present)
            import json
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_text)
        except Exception as e:
            print(f"Gemini API call failed, falling back to keyword heuristics: {e}")

    # Keyword backup heuristics
    category = "other"
    suggested_title = "Community Civic Issue"
    tags = ["Community"]
    severity = "medium"
    confidence = 0.82

    if "pot" in desc_lower or "road" in desc_lower or "hole" in desc_lower:
        category = "pothole"
        suggested_title = "Damaged Road Pothole"
        tags = ["RoadSafety", "Infrastructure"]
        severity = "critical" if "deep" in desc_lower or "huge" in desc_lower else "high"
        confidence = 0.94
    elif "water" in desc_lower or "leak" in desc_lower or "pipe" in desc_lower:
        category = "water_leak"
        suggested_title = "Water Supply Leakage"
        tags = ["WaterConservation", "UtilityLeak"]
        severity = "high" if "gushing" in desc_lower else "medium"
        confidence = 0.92
    elif "light" in desc_lower or "bulb" in desc_lower or "dark" in desc_lower:
        category = "streetlight"
        suggested_title = "Faulty Streetlight"
        tags = ["Streetlighting", "SafetyAtNight"]
        severity = "high" if "dark" in desc_lower else "medium"
        confidence = 0.96
    elif "garbage" in desc_lower or "waste" in desc_lower or "trash" in desc_lower or "dump" in desc_lower:
        category = "waste"
        suggested_title = "Accumulated Waste Dump"
        tags = ["WasteManagement", "Sanitation"]
        severity = "critical" if "stink" in desc_lower else "high"
        confidence = 0.97

    return {
        "category": category,
        "severity": severity,
        "tags": tags,
        "suggestedTitle": suggested_title,
        "confidence": confidence
    }

# ==========================================
# GAMIFICATION LOGIC
# ==========================================
def award_user_xp(conn, user_id, action_type):
    xp_gains = {
        "submit_report": 10,
        "verify_report": 5,
        "report_resolved": 50,
        "comment": 2
    }
    gain = xp_gains.get(action_type, 0)
    if gain == 0:
        return
        
    if conn:
        # Real Database operation
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Update base counts
                if action_type == "submit_report":
                    cur.execute("UPDATE users SET xp_points = xp_points + %s, reports_count = reports_count + 1 WHERE id = %s RETURNING reports_count, verified_count, badge_ids", (gain, user_id))
                elif action_type == "verify_report":
                    cur.execute("UPDATE users SET xp_points = xp_points + %s, verified_count = verified_count + 1 WHERE id = %s RETURNING reports_count, verified_count, badge_ids", (gain, user_id))
                else:
                    cur.execute("UPDATE users SET xp_points = xp_points + %s WHERE id = %s RETURNING reports_count, verified_count, badge_ids", (gain, user_id))
                
                user = cur.fetchone()
                if user:
                    reports_count = user["reports_count"]
                    verified_count = user["verified_count"]
                    current_badge_ids = user["badge_ids"] or []
                    
                    # Fetch badges to check criteria
                    cur.execute("SELECT id, condition_type, condition_value FROM badges")
                    all_badges = cur.fetchall()
                    newly_earned = list(current_badge_ids)
                    
                    for badge in all_badges:
                        if badge["id"] not in newly_earned:
                            if badge["condition_type"] == "reports_count" and reports_count >= badge["condition_value"]:
                                newly_earned.append(badge["id"])
                            elif badge["condition_type"] == "verified_count" and verified_count >= badge["condition_value"]:
                                newly_earned.append(badge["id"])
                                
                    if len(newly_earned) > len(current_badge_ids):
                        cur.execute("UPDATE users SET badge_ids = %s WHERE id = %s", (newly_earned, user_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error awarding XP: {e}")
    else:
        # Mock database fallback
        user = next((u for u in mock_db["users"] if u["id"] == user_id), None)
        if user:
            user["xpPoints"] += gain
            if action_type == "submit_report":
                user["reportsCount"] += 1
            elif action_type == "verify_report":
                user["verifiedCount"] += 1
                
            # Check badge conditions
            current_badges = list(user["badgeIds"])
            for badge in mock_db["badges"]:
                if badge["id"] not in current_badges:
                    if badge["conditionType"] == "reports_count" and user["reportsCount"] >= badge["conditionValue"]:
                        current_badges.append(badge["id"])
                    elif badge["conditionType"] == "verified_count" and user["verifiedCount"] >= badge["conditionValue"]:
                        current_badges.append(badge["id"])
            user["badgeIds"] = current_badges

# ==========================================
# REST API ENDPOINTS
# ==========================================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "database_connected": DB_URL is not None,
        "gemini_api_configured": GEMINI_KEY is not None,
        "timestamp": datetime.utcnow().isoformat()
    })

# 1. FETCH ALL REPORTS
@app.route("/api/reports", methods=["GET"])
def get_reports():
    conn = get_db_connection()
    
    category = request.args.get("category", "all")
    severity = request.args.get("severity", "all")
    status = request.args.get("status", "all")
    search = request.args.get("search", "")

    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM issues WHERE 1=1"
                params = []
                
                if category != "all":
                    query += " AND category = %s"
                    params.append(category)
                if severity != "all":
                    query += " AND severity = %s"
                    params.append(severity)
                if status != "all":
                    query += " AND status = %s"
                    params.append(status)
                if search:
                    query += " AND (title ILIKE %s OR description ILIKE %s OR address_text ILIKE %s)"
                    like_term = f"%{search}%"
                    params.extend([like_term, like_term, like_term])
                    
                query += " ORDER BY created_at DESC"
                cur.execute(query, params)
                rows = cur.fetchall()
                
                # Format to JSON schema
                issues = []
                for row in rows:
                    issues.append({
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "category": row["category"],
                        "severity": row["severity"],
                        "status": row["status"],
                        "mediaUrls": row["media_urls"],
                        "latitude": row["latitude"],
                        "longitude": row["longitude"],
                        "addressText": row["address_text"],
                        "wardId": row["ward_id"],
                        "reporterId": row["reporter_id"],
                        "assignedTo": row["assigned_to"],
                        "aiCategory": row["ai_category"],
                        "aiConfidence": row["ai_confidence"],
                        "upvoteCount": row["upvote_count"],
                        "isDuplicate": row["is_duplicate"],
                        "duplicateOf": row["duplicate_of"],
                        "createdAt": row["created_at"].isoformat() if row["created_at"] else None,
                        "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
                        "resolvedAt": row["resolved_at"].isoformat() if row["resolved_at"] else None,
                    })
                return jsonify(issues)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    else:
        # Fallback to local memory filter
        res = []
        for iss in mock_db["issues"]:
            if category != "all" and iss["category"] != category: continue
            if severity != "all" and iss["severity"] != severity: continue
            if status != "all" and iss["status"] != status: continue
            if search and not (search.lower() in iss["title"].lower() or search.lower() in iss["description"].lower()): continue
            res.append(iss)
        return jsonify(res)

# 2. RUN AI PRE-SCAN
@app.route("/api/reports/ai-scan", methods=["POST"])
def ai_scan():
    data = request.get_json() or {}
    description = data.get("description", "")
    
    analysis = run_ai_analysis(description)
    return jsonify(analysis)

# 3. CREATE NEW CIVIC REPORT
@app.route("/api/reports", methods=["POST"])
def create_report():
    data = request.get_json() or {}
    
    title = data.get("title")
    description = data.get("description", "")
    category = data.get("category")
    severity = data.get("severity", "medium")
    latitude = float(data.get("latitude", 12.9716))
    longitude = float(data.get("longitude", 77.5946))
    address_text = data.get("addressText", "Bengaluru")
    media_url = data.get("mediaUrl") or "https://images.unsplash.com/photo-1599740831464-54c478627ec3?auto=format&fit=crop&w=800&q=80"
    reporter_id = data.get("reporterId", "u1")
    
    if not title or not category:
        return jsonify({"error": "Missing title or category"}), 400
        
    issue_id = f"iss-{uuid.uuid4().hex[:8]}"
    
    # 3.1 Proximity duplicate scanning (150 meters ~ 0.00135 coordinate threshold)
    is_duplicate = False
    duplicate_of = None
    
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Find near active reports of same category
                cur.execute("""
                    SELECT id FROM issues 
                    WHERE category = %s AND status != 'resolved' AND status != 'rejected'
                    AND ABS(latitude - %s) <= 0.00135 AND ABS(longitude - %s) <= 0.00135
                    LIMIT 1
                """, (category, latitude, longitude))
                dup = cur.fetchone()
                if dup:
                    is_duplicate = True
                    duplicate_of = dup["id"]
                    
                # Insert report
                cur.execute("""
                    INSERT INTO issues (id, title, description, category, severity, status, media_urls, latitude, longitude, address_text, reporter_id, is_duplicate, duplicate_of)
                    VALUES (%s, %s, %s, %s, %s, 'reported', %s, %s, %s, %s, %s, %s, %s)
                """, (issue_id, title, description, category, severity, [media_url], latitude, longitude, address_text, reporter_id, is_duplicate, duplicate_of))
                
                # Create history log
                log_id = f"sh-{uuid.uuid4().hex[:8]}"
                cur.execute("""
                    INSERT INTO status_history (id, issue_id, changed_by, old_status, new_status, note)
                    VALUES (%s, %s, %s, NULL, 'reported', 'Citizen submission logged in system.')
                """, (log_id, issue_id, reporter_id))
            
            conn.commit()
            award_user_xp(conn, reporter_id, "submit_report")
            
            return jsonify({
                "id": issue_id,
                "message": "Report logged successfully",
                "isDuplicate": is_duplicate,
                "duplicateOf": duplicate_of
            }), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    else:
        # Local mock duplication scan
        for iss in mock_db["issues"]:
            if iss["category"] == category and iss["status"] not in ["resolved", "rejected"]:
                if abs(iss["latitude"] - latitude) <= 0.00135 and abs(iss["longitude"] - longitude) <= 0.00135:
                    is_duplicate = True
                    duplicate_of = iss["id"]
                    break
                    
        new_issue = {
            "id": issue_id,
            "title": title,
            "description": description,
            "category": category,
            "severity": severity,
            "status": "reported",
            "mediaUrls": [media_url],
            "latitude": latitude,
            "longitude": longitude,
            "addressText": address_text,
            "wardId": "w1",
            "reporterId": reporter_id,
            "assignedTo": None,
            "aiCategory": category,
            "aiConfidence": 0.95,
            "upvoteCount": 0,
            "isDuplicate": is_duplicate,
            "duplicateOf": duplicate_of,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "updatedAt": datetime.utcnow().isoformat() + "Z",
            "resolvedAt": None
        }
        
        mock_db["issues"].insert(0, new_issue)
        mock_db["statusHistory"].append({
            "id": f"sh-{uuid.uuid4().hex[:8]}",
            "issueId": issue_id,
            "changedBy": reporter_id,
            "oldStatus": None,
            "newStatus": "reported",
            "note": "Citizen submission logged in system.",
            "createdAt": datetime.utcnow().isoformat() + "Z"
        })
        
        award_user_xp(None, reporter_id, "submit_report")
        
        return jsonify({
            "id": issue_id,
            "message": "Report logged successfully (mock fallback database)",
            "isDuplicate": is_duplicate,
            "duplicateOf": duplicate_of
        }), 201

# 4. UPVOTE & VERIFY
@app.route("/api/reports/<issue_id>/verify", methods=["POST"])
def verify_report(issue_id):
    data = request.get_json() or {}
    user_id = data.get("userId", "u1")
    
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Add verification relation
                v_id = f"v-{uuid.uuid4().hex[:8]}"
                try:
                    cur.execute("""
                        INSERT INTO verifications (id, issue_id, user_id, type)
                        VALUES (%s, %s, %s, 'upvote')
                    """, (v_id, issue_id, user_id))
                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    return jsonify({"error": "User already upvoted this report"}), 400
                
                # Fetch current upvote details
                cur.execute("SELECT upvote_count, status, title FROM issues WHERE id = %s", (issue_id,))
                iss = cur.fetchone()
                if not iss:
                    return jsonify({"error": "Issue not found"}), 440
                    
                new_votes = iss["upvote_count"] + 1
                new_status = iss["status"]
                
                # Auto verification threshold check
                if iss["status"] == "reported" and new_votes >= 5:
                    new_status = "verified"
                    sh_id = f"sh-{uuid.uuid4().hex[:8]}"
                    cur.execute("""
                        INSERT INTO status_history (id, issue_id, changed_by, old_status, new_status, note)
                        VALUES (%s, %s, %s, 'reported', 'verified', 'Automated trigger: Community support threshold reached (5+ verifications).')
                    """, (sh_id, issue_id, user_id))
                    
                cur.execute("UPDATE issues SET upvote_count = %s, status = %s WHERE id = %s", (new_votes, new_status, issue_id))
            conn.commit()
            award_user_xp(conn, user_id, "verify_report")
            
            return jsonify({"message": "Upvote and verification processed successfully"}), 200
        except Exception as e:
            if conn: conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            if conn: conn.close()
    else:
        # Mock upvote
        iss = next((i for i in mock_db["issues"] if i["id"] == issue_id), None)
        if not iss:
            return jsonify({"error": "Issue not found"}), 404
            
        already_v = any(v for v in mock_db["verifications"] if v["issueId"] == issue_id and v["userId"] == user_id)
        if already_v:
            return jsonify({"error": "User already upvoted this report"}), 400
            
        mock_db["verifications"].append({
            "id": f"v-{uuid.uuid4().hex[:8]}",
            "issueId": issue_id,
            "userId": user_id,
            "type": "upvote",
            "createdAt": datetime.utcnow().isoformat() + "Z"
        })
        
        iss["upvoteCount"] += 1
        if iss["status"] == "reported" and iss["upvoteCount"] >= 5:
            iss["status"] = "verified"
            mock_db["statusHistory"].append({
                "id": f"sh-{uuid.uuid4().hex[:8]}",
                "issueId": issue_id,
                "changedBy": user_id,
                "oldStatus": "reported",
                "newStatus": "verified",
                "note": "Automated trigger: Community support threshold reached (5+ verifications).",
                "createdAt": datetime.utcnow().isoformat() + "Z"
            })
            
        award_user_xp(None, user_id, "verify_report")
        return jsonify({"message": "Upvote processed successfully (mock database)"}), 200

# 5. SUBMIT COMMENT
@app.route("/api/reports/<issue_id>/comments", methods=["POST"])
def post_comment(issue_id):
    data = request.get_json() or {}
    user_id = data.get("userId")
    content = data.get("content")
    
    if not user_id or not content:
        return jsonify({"error": "Missing parameters"}), 400
        
    c_id = f"c-{uuid.uuid4().hex[:8]}"
    
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check user role
                cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
                usr = cur.fetchone()
                is_authority = usr["role"] == "authority" if usr else False
                
                cur.execute("""
                    INSERT INTO comments (id, issue_id, user_id, content, is_authority)
                    VALUES (%s, %s, %s, %s, %s)
                """, (c_id, issue_id, user_id, content, is_authority))
            conn.commit()
            award_user_xp(conn, user_id, "comment")
            return jsonify({"message": "Comment submitted successfully"}), 200
        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    else:
        user = next((u for u in mock_db["users"] if u["id"] == user_id), None)
        is_auth = user["role"] == "authority" if user else False
        
        mock_db["comments"].append({
            "id": c_id,
            "issueId": issue_id,
            "userId": user_id,
            "content": content,
            "isAuthority": is_auth,
            "createdAt": datetime.utcnow().isoformat() + "Z"
        })
        award_user_xp(None, user_id, "comment")
        return jsonify({"message": "Comment submitted successfully (mock database)"}), 200

# 6. GET COMMENTS AND HISTORY FOR AN ISSUE
@app.route("/api/reports/<issue_id>/details", methods=["GET"])
def get_issue_details(issue_id):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM comments WHERE issue_id = %s ORDER BY created_at ASC", (issue_id,))
                comments = cur.fetchall()
                
                cur.execute("SELECT * FROM status_history WHERE issue_id = %s ORDER BY created_at ASC", (issue_id,))
                history = cur.fetchall()
                
                return jsonify({
                    "comments": comments,
                    "history": history
                })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    else:
        comments = [c for c in mock_db["comments"] if c["issueId"] == issue_id]
        history = [h for h in mock_db["statusHistory"] if h["issueId"] == issue_id]
        return jsonify({
            "comments": comments,
            "history": history
        })

# 7. UPDATE TICKET STATUS (AUTHORITY)
@app.route("/api/reports/<issue_id>/status", methods=["PUT"])
def update_issue_status(issue_id):
    data = request.get_json() or {}
    new_status = data.get("status")
    changed_by = data.get("changedBy")
    note = data.get("note", "")
    
    if not new_status or not changed_by:
        return jsonify({"error": "Missing status or user ID"}), 400
        
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT status, reporter_id FROM issues WHERE id = %s", (issue_id,))
                iss = cur.fetchone()
                if not iss:
                    return jsonify({"error": "Issue not found"}), 404
                    
                old_status = iss["status"]
                reporter_id = iss["reporter_id"]
                
                resolved_time = datetime.utcnow() if new_status == "resolved" else None
                
                # Update status
                cur.execute("""
                    UPDATE issues 
                    SET status = %s, resolved_at = %s, updated_at = NOW() 
                    WHERE id = %s
                """, (new_status, resolved_time, issue_id))
                
                # History log
                sh_id = f"sh-{uuid.uuid4().hex[:8]}"
                cur.execute("""
                    INSERT INTO status_history (id, issue_id, changed_by, old_status, new_status, note)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (sh_id, issue_id, changed_by, old_status, new_status, note))
                
            conn.commit()
            
            # Award reporter +50 XP if resolved
            if new_status == "resolved":
                award_user_xp(conn, reporter_id, "report_resolved")
                
            return jsonify({"message": "Status advanced successfully"}), 200
        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    else:
        # Mock DB
        iss = next((i for i in mock_db["issues"] if i["id"] == issue_id), None)
        if not iss:
            return jsonify({"error": "Issue not found"}), 404
            
        old_status = iss["status"]
        iss["status"] = new_status
        iss["updatedAt"] = datetime.utcnow().isoformat() + "Z"
        
        if new_status == "resolved":
            iss["resolvedAt"] = datetime.utcnow().isoformat() + "Z"
            award_user_xp(None, iss["reporterId"], "report_resolved")
            
        mock_db["statusHistory"].append({
            "id": f"sh-{uuid.uuid4().hex[:8]}",
            "issueId": issue_id,
            "changedBy": changed_by,
            "oldStatus": old_status,
            "newStatus": new_status,
            "note": note,
            "createdAt": datetime.utcnow().isoformat() + "Z"
        })
        return jsonify({"message": "Status updated successfully (mock database)"}), 200

# 8. FETCH USER PROFILE & LEADERBOARDS
@app.route("/api/users/<user_id>", methods=["GET"])
def get_user_profile(user_id):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                user = cur.fetchone()
                if not user:
                    return jsonify({"error": "User not found"}), 404
                return jsonify(user)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    else:
        user = next((u for u in mock_db["users"] if u["id"] == user_id), None)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user)

@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM users WHERE role = 'citizen' ORDER BY xp_points DESC")
                users = cur.fetchall()
                return jsonify(users)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    else:
        citizens = [u for u in mock_db["users"] if u["role"] == "citizen"]
        citizens.sort(key=lambda x: x["xpPoints"], reverse=True)
        return jsonify(citizens)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

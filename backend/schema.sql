-- PostgreSQL database schema configuration for Community Hero

-- Drop existing tables if they exist to start fresh (in order of dependencies)
DROP TABLE IF EXISTS comments CASCADE;
DROP TABLE IF EXISTS verifications CASCADE;
DROP TABLE IF EXISTS status_history CASCADE;
DROP TABLE IF EXISTS issues CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS wards CASCADE;
DROP TABLE IF EXISTS badges CASCADE;

-- 1. WARDS TABLE
CREATE TABLE wards (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    boundary_geojson JSONB
);

-- 2. BADGES TABLE
CREATE TABLE badges (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(10) NOT NULL,
    description TEXT NOT NULL,
    xp_reward INTEGER NOT NULL DEFAULT 0,
    condition_type VARCHAR(50) NOT NULL,
    condition_value INTEGER NOT NULL
);

-- 3. USERS TABLE
CREATE TABLE users (
    id VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    phone VARCHAR(50),
    avatar_url TEXT,
    role VARCHAR(50) NOT NULL DEFAULT 'citizen', -- citizen, moderator, authority, admin
    ward_id VARCHAR(50) REFERENCES wards(id) ON DELETE SET NULL,
    xp_points INTEGER NOT NULL DEFAULT 0,
    badge_ids TEXT[] DEFAULT '{}',
    reports_count INTEGER NOT NULL DEFAULT 0,
    verified_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. ISSUES TABLE
CREATE TABLE issues (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL, -- pothole, water_leak, streetlight, waste, road_damage, other
    severity VARCHAR(50) NOT NULL DEFAULT 'medium', -- low, medium, high, critical
    status VARCHAR(50) NOT NULL DEFAULT 'reported', -- reported, verified, assigned, in_progress, resolved, rejected
    media_urls TEXT[] DEFAULT '{}',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    address_text TEXT,
    ward_id VARCHAR(50) REFERENCES wards(id) ON DELETE SET NULL,
    reporter_id VARCHAR(50) REFERENCES users(id) ON DELETE SET NULL,
    assigned_to VARCHAR(50) REFERENCES users(id) ON DELETE SET NULL,
    ai_category VARCHAR(50),
    ai_confidence DOUBLE PRECISION,
    upvote_count INTEGER NOT NULL DEFAULT 0,
    is_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    duplicate_of VARCHAR(50) REFERENCES issues(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- 5. VERIFICATIONS TABLE
CREATE TABLE verifications (
    id VARCHAR(50) PRIMARY KEY,
    issue_id VARCHAR(50) REFERENCES issues(id) ON DELETE CASCADE,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL DEFAULT 'upvote', -- upvote, seen, dispute
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_verification UNIQUE (issue_id, user_id)
);

-- 6. COMMENTS TABLE
CREATE TABLE comments (
    id VARCHAR(50) PRIMARY KEY,
    issue_id VARCHAR(50) REFERENCES issues(id) ON DELETE CASCADE,
    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    is_authority BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. STATUS HISTORY LOGS
CREATE TABLE status_history (
    id VARCHAR(50) PRIMARY KEY,
    issue_id VARCHAR(50) REFERENCES issues(id) ON DELETE CASCADE,
    changed_by VARCHAR(50) REFERENCES users(id) ON DELETE SET NULL,
    old_status VARCHAR(50),
    new_status VARCHAR(50) NOT NULL,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- SEED DATA INSERTIONS

-- Wards
INSERT INTO wards (id, name, city) VALUES 
('w1', 'Indiranagar', 'Bengaluru'),
('w2', 'Koramangala', 'Bengaluru'),
('w3', 'HSR Layout', 'Bengaluru'),
('w4', 'Whitefield', 'Bengaluru');

-- Badges
INSERT INTO badges (id, name, icon, description, xp_reward, condition_type, condition_value) VALUES 
('b1', 'First Reporter', '🏅', 'Submit your first report', 50, 'reports_count', 1),
('b2', 'Neighborhood Watch', '👁️', 'Verify 5 issues reported by others', 100, 'verified_count', 5),
('b3', 'Problem Solver', '🛠️', 'Have 3 of your reported issues successfully resolved', 150, 'resolved_count', 3),
('b4', 'Ward Champion', '👑', 'Submit 10 reports in a single month', 200, 'reports_count', 10);

-- Users
INSERT INTO users (id, email, full_name, phone, avatar_url, role, ward_id, xp_points, badge_ids, reports_count, verified_count) VALUES 
('u1', 'aditya@communityhero.in', 'Aditya Kumar', '+91 98765 43210', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&h=150', 'citizen', 'w1', 120, ARRAY['b1'], 3, 4),
('u2', 'priya@communityhero.in', 'Priya Sharma', '+91 98123 45678', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=150&h=150', 'citizen', 'w2', 240, ARRAY['b1', 'b2'], 8, 12),
('u3', 'rohan.mod@communityhero.in', 'Rohan Sen', '+91 99000 88888', 'https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=150&h=150', 'moderator', 'w3', 350, ARRAY['b1', 'b2', 'b3'], 12, 45),
('u4', 'officer.ramesh@bbmp.gov.in', 'Officer Ramesh Gowda', '+91 98888 77777', 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&h=150', 'authority', 'w1', 0, ARRAY[]::TEXT[], 0, 0),
('u5', 'admin@communityhero.in', 'Super Admin', '+91 90000 00000', 'https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=150&h=150', 'admin', 'w3', 10, ARRAY[]::TEXT[], 0, 0);

-- Initial Issues
INSERT INTO issues (id, title, description, category, severity, status, media_urls, latitude, longitude, address_text, ward_id, reporter_id, assigned_to, ai_category, ai_confidence, upvote_count) VALUES 
('iss1', 'Deep Pothole on Indiranagar 100ft Road', 'Huge pothole right in the middle of the road near the corner turn. Causes vehicles to swerve dangerously, especially two-wheelers at night. Needs immediate asphalt filling.', 'pothole', 'critical', 'verified', ARRAY['https://images.unsplash.com/photo-1515162305285-0293e4767cc2?auto=format&fit=crop&w=800&q=80'], 12.9784, 77.6408, 'Indiranagar 100 Feet Rd, Hal 2nd Stage, Indiranagar, Bengaluru, Karnataka 560038', 'w1', 'u2', NULL, 'pothole', 0.96, 15),
('iss2', 'Broken Streetlight Near Metro Station', 'The streetlight has been flicking for a week and has now completely died. The alley is pitch dark and unsafe for commuters walking home late.', 'streetlight', 'high', 'in_progress', ARRAY['https://images.unsplash.com/photo-1509024644558-2f56ce76c490?auto=format&fit=crop&w=800&q=80'], 12.9722, 77.6320, 'Chinmaya Mission Hospital Rd, Indiranagar, Bengaluru, Karnataka 560038', 'w1', 'u1', 'u4', 'streetlight', 0.98, 7),
('iss3', 'Major Water Pipe Leakage', 'Clean water has been gushing out of a cracked pipe under the pavement. Massive wastage of water. It has formed a mini-pond.', 'water_leak', 'medium', 'resolved', ARRAY['https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=800&q=80'], 12.9352, 77.6245, '80 Feet Rd, 4th Block, Koramangala, Bengaluru, Karnataka 560034', 'w2', 'u2', 'u4', 'water_leak', 0.94, 22),
('iss4', 'Illegal Garbage Dumping on Sidewalk', 'Tons of plastic waste and organic garbage dumped on the corner of the layout park. It is starting to smell awful and attracting stray dogs.', 'waste', 'critical', 'reported', ARRAY['https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=800&q=80'], 12.9116, 77.6388, '24th Main Rd, Sector 2, HSR Layout, Bengaluru, Karnataka 560102', 'w3', 'u1', NULL, 'waste', 0.99, 4),
('iss5', 'Cracked Road and Caved-in Edge', 'The side of the asphalt has eroded and caved in. Heavy vehicles parking on the shoulder could trigger a slide or roll over.', 'road_damage', 'high', 'reported', ARRAY['https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=800&q=80'], 12.9698, 77.7500, 'ITPL Main Rd, Pattandur Agrahara, Whitefield, Bengaluru, Karnataka 560066', 'w4', 'u2', NULL, 'road_damage', 0.89, 8);

-- Verifications
INSERT INTO verifications (id, issue_id, user_id, type) VALUES 
('v1', 'iss1', 'u1', 'upvote'),
('v2', 'iss1', 'u3', 'seen'),
('v3', 'iss2', 'u2', 'upvote'),
('v4', 'iss3', 'u1', 'upvote'),
('v5', 'iss3', 'u3', 'upvote');

-- Comments
INSERT INTO comments (id, issue_id, user_id, content, is_authority) VALUES 
('c1', 'iss1', 'u1', 'I almost fell here on my scooter yesterday. Extremely dangerous, glad it was reported!', FALSE),
('c2', 'iss1', 'u3', 'Verified this in person today. The depth is around 8 inches.', FALSE),
('c3', 'iss2', 'u4', 'Assigned to the local electrical ward team. We are procuring a replacement bulb.', TRUE),
('c4', 'iss3', 'u4', 'Water board team has successfully welded the pipe joint. The supply leak is stopped.', TRUE);

-- Status History Logs
INSERT INTO status_history (id, issue_id, changed_by, old_status, new_status, note) VALUES 
('sh1', 'iss1', 'u2', NULL, 'reported', 'Initial submission'),
('sh2', 'iss1', 'u3', 'reported', 'verified', 'Verified depth and safety threat'),
('sh3', 'iss2', 'u1', NULL, 'reported', 'Initial submission'),
('sh4', 'iss2', 'u4', 'reported', 'in_progress', 'Assigned to electric maintenance team'),
('sh5', 'iss3', 'u2', NULL, 'reported', 'Initial submission'),
('sh6', 'iss3', 'u4', 'reported', 'in_progress', 'Technicians dispatched'),
('sh7', 'iss3', 'u4', 'in_progress', 'resolved', 'Leak plugged, pavement restored.');

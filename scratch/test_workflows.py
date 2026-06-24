import os
os.environ['TESTING'] = 'True'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
import unittest
import app as app_module
from app import app, db, User, Issue, haversine_distance

# Mock the geocoding functions to avoid slow network queries during tests
app_module.geocode_address = lambda address: (12.9716, 77.5946, "Bangalore Urban", "Karnataka")
app_module.reverse_geocode = lambda lat, lon: ("Bangalore Urban", "Karnataka")

class CommunityHeroTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SECRET_KEY'] = 'test-secret-key'
        app.config['WTF_CSRF_ENABLED'] = False
        
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()
        
        db.create_all()
        self.seed_test_data()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def seed_test_data(self):
        # Create Admin
        admin = User(username='admin', email='admin@test.com', role='admin')
        admin.set_password('password123')
        db.session.add(admin)
        db.session.commit()
        
        # Create State Manager
        sm = User(username='state_mgr', email='state@test.com', role='state_manager', state='Karnataka', created_by_id=admin.id)
        sm.set_password('password123')
        db.session.add(sm)
        db.session.commit()

        # Create District Manager
        dm = User(username='dist_mgr', email='dist@test.com', role='district_manager', state='Karnataka', district='Bangalore Urban', created_by_id=sm.id)
        dm.set_password('password123')
        db.session.add(dm)
        db.session.commit()

        # Create Citizen (Bangalore)
        citizen = User(
            username='alex', 
            email='alex@test.com', 
            role='citizen', 
            state='Karnataka', 
            district='Bangalore Urban',
            address='MG Road, Bangalore',
            latitude=12.9716, 
            longitude=77.5946,
            points=100
        )
        citizen.set_password('password123')
        db.session.add(citizen)
        db.session.commit()

    def login(self, username, password='password123'):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_role_hierarchy_creation(self):
        # Login as Admin
        self.login('admin')
        # Create a new State Manager
        response = self.client.post('/api/managers/state', data=dict(
            username='new_state_mgr',
            email='new_state@test.com',
            password='password123',
            state='Maharashtra'
        ), follow_redirects=True)
        self.assertIn(b'Successfully created State Manager for Maharashtra', response.data)
        
        # Verify db entry
        user = User.query.filter_by(username='new_state_mgr').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, 'state_manager')
        self.assertEqual(user.state, 'Maharashtra')
        self.logout()

        # Login as the State Manager
        self.login('state_mgr')
        # Create a new District Manager
        response = self.client.post('/api/managers/district', data=dict(
            username='new_dist_mgr',
            email='new_dist@test.com',
            password='password123',
            district='Mysore'
        ), follow_redirects=True)
        self.assertIn(b'Successfully created District Manager for Mysore', response.data)
        
        # Verify db entry
        user2 = User.query.filter_by(username='new_dist_mgr').first()
        self.assertIsNotNone(user2)
        self.assertEqual(user2.role, 'district_manager')
        self.assertEqual(user2.state, 'Karnataka')  # Inherited from state manager scope
        self.assertEqual(user2.district, 'Mysore')

    def test_issue_range_limits(self):
        self.login('alex')
        
        # 1. Report issue within range (1 km away)
        # alex home is 12.9716, 77.5946
        # target location is 12.9720, 77.5950
        response = self.client.post('/api/issues/report', data=dict(
            title='Leaky Water Line',
            description='Water is pooling near the sidewalk.',
            intensity='Medium',
            latitude='12.9720',
            longitude='77.5950',
            user_latitude='12.9716',
            user_longitude='77.5946'
        ))
        data = response.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('Leaky Water Line', Issue.query.first().title)

        # 2. Report issue out of range (50 km away, e.g. 13.5, 78.5)
        response_fail = self.client.post('/api/issues/report', data=dict(
            title='Distant Garbage Pile',
            description='Trash piled up on the highway.',
            intensity='High',
            latitude='13.5000',
            longitude='78.5000',
            user_latitude='12.9716',
            user_longitude='77.5946'
        ))
        data_fail = response_fail.get_json()
        self.assertFalse(data_fail.get('success', False))
        self.assertIn('error', data_fail)
        self.assertIn('Cannot report an issue located more than 10 KM away', data_fail.get('error'))

    def test_govt_updates_and_citizen_challenges(self):
        # Create an issue
        citizen = User.query.filter_by(username='alex').first()
        issue = Issue(
            title='Pothole',
            description='A huge pothole.',
            intensity='High',
            category='Roads',
            latitude=12.9716,
            longitude=77.5946,
            status='Open',
            govt_status='NOT VISITED',
            state='Karnataka',
            district='Bangalore Urban',
            user_id=citizen.id
        )
        db.session.add(issue)
        db.session.commit()
        
        # Login as district manager and update status to DONE
        self.login('dist_mgr')
        response = self.client.post(f'/api/issues/{issue.id}/govt_update', data=dict(
            govt_status='DONE',
            content='Pothole has been patched with hot mix asphalt.'
        ))
        self.assertTrue(response.get_json().get('success'))
        
        # Check database updates
        issue_db = Issue.query.get(issue.id)
        self.assertEqual(issue_db.govt_status, 'DONE')
        self.assertEqual(issue_db.status, 'Resolved')
        self.logout()

        # Login as citizen reporter and challenge the DONE status
        self.login('alex')
        response_challenge = self.client.post(f'/api/issues/{issue.id}/challenge', json=dict(
            content='The patch has already sunk and cracked open again.'
        ))
        self.assertTrue(response_challenge.get_json().get('success'))
        
        # Verify reverted status
        issue_db2 = Issue.query.get(issue.id)
        self.assertEqual(issue_db2.govt_status, 'NOT VISITED')
        self.assertEqual(issue_db2.status, 'Open')

if __name__ == '__main__':
    unittest.main()

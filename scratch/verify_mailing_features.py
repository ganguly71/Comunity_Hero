import os
import sys

# Ensure Vibe2Ship path is imported
sys.path.append(r'c:\Users\adity\OneDrive\ドキュメント\Vibe2Ship')

from app import app, db, send_brevo_email, User, Issue, SentMail
from unittest.mock import patch

def test_mailing_system():
    print("=== Testing Mailing and Secure Logging System ===")
    
    with app.app_context():
        # Ensure tables exist
        db.create_all()

        # 1. Test Brevo Direct Helper
        print("\n1. Testing send_brevo_email helper...")
        with patch('requests.post') as mock_post:
            # Mock success response from Brevo
            mock_post.return_value.status_code = 201
            mock_post.return_value.text = '{"messageId": "test-id"}'
            
            # Temporarily configure environment keys for testing
            os.environ['BREVO_API_KEY'] = 'test-api-key-123'
            
            res = send_brevo_email(
                to_email="reporter@test.com",
                to_name="Test Reporter",
                subject="Test Subject",
                html_content="<p>Test Body</p>",
                reply_to_email="manager@test.com",
                reply_to_name="Test Manager"
            )
            print(f"Result (should be True): {res}")
            assert res is True
            print("send_brevo_email helper test passed!")

        # 2. Test DB Model insertions
        print("\n2. Testing SentMail database log generation...")
        
        # Grab standard seeded manager and reporter user from DB
        mgr = User.query.filter_by(role='district_manager').first()
        reporter = User.query.filter_by(role='citizen').first()
        issue = Issue.query.first()
        
        if not mgr or not reporter or not issue:
            print("Warning: Database might be empty. Seed database or run server first.")
            return

        # Insert a SentMail log
        mail_log = SentMail(
            sender_id=mgr.id,
            receiver_id=reporter.id,
            issue_id=issue.id,
            subject="Additional photo request",
            body="Can you upload a better photo of the pothole?"
        )
        db.session.add(mail_log)
        db.session.commit()
        
        # Verify it was committed successfully
        saved = SentMail.query.filter_by(subject="Additional photo request").first()
        assert saved is not None
        print(f"Saved mail log: ID={saved.id}, Sender={saved.sender.username}, Receiver={saved.receiver.username}, Issue={saved.issue.title}")
        
        # Clean up test log
        db.session.delete(saved)
        db.session.commit()
        print("SentMail DB model verification passed!")

if __name__ == '__main__':
    test_mailing_system()

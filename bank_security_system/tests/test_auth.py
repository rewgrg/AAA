import unittest
from app import create_app
from models.user import User

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        with self.app.app_context():
            User.query.delete()
            user = User(username='test', password='test123')
            user.set_password('test123')
            db.session.add(user)
            db.session.commit()

    def test_login(self):
        res = self.client.post('/api/auth/login', json={
            'username': 'test',
            'password': 'test123'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.json)
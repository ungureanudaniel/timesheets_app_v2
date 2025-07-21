from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate


class CustomAuthenticationBackendTests(TestCase):
    def setUp(self):
        """Create test users with various attributes."""
        UserModel = get_user_model()

        # Create users for testing
        self.valid_user = UserModel.objects.create_user(
            username='validuser',
            email='valid@example.com',
            password='securepassword',
            is_person=True
        )

        self.invalid_user = UserModel.objects.create_user(
            username='invaliduser',
            email='invalid@example.com',
            password='securepassword',
            is_person=False
        )

    def test_valid_user_authentication(self):
        """Test that a user with `is_person=True` can authenticate successfully."""
        user = authenticate(username='validuser', password='securepassword')
        self.assertIsNotNone(user)
        self.assertTrue(user.is_person)

    def test_invalid_user_authentication(self):
        """Test that a user with `is_person=False` cannot authenticate."""
        user = authenticate(username='invaliduser', password='securepassword')
        self.assertIsNone(user)

    def test_login_view(self):
        """Test that login view works correctly with valid credentials."""
        response = self.client.post('/accounts/login/', {
            'username': 'validuser',
            'password': 'securepassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Logged in successfully')

    def test_login_view_invalid_user(self):
        """Test that login view fails with invalid user credentials."""
        response = self.client.post('/accounts/login/', {
            'username': 'invaliduser',
            'password': 'securepassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid login credentials')

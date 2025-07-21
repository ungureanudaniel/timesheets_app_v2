from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.core import mail
from users.forms import CustomUserCreationForm

User = get_user_model()


# =========USER MODEL TEST========================
class CustomUserModelTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='REPORTER')
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertFalse(self.user.is_approved)  # By default, user should not be approved
        self.assertEqual(self.user.groups.count(), 0)  # User should not belong to any group initially

    def test_assign_initial_group(self):
        self.user.assign_initial_group()
        self.assertEqual(self.user.groups.count(), 1)
        self.assertIn(self.group, self.user.groups.all())

    def test_user_string_representation(self):
        self.assertEqual(str(self.user), 'testuser')


# =========USER REGISTRATION VIEW TEST========================
class RegisterViewTests(TestCase):
    def setUp(self):
        self.group_timesheets_input = Group.objects.create(name='REPORTER')

    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

    def test_register_view_post_valid_form(self):
        form_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
        }
        response = self.client.post(reverse('register'), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/profile.html')

        self.assertTrue(User.objects.filter(username='newuser').exists())
        new_user = User.objects.get(username='newuser')
        self.assertFalse(new_user.is_approved)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('New User Access Request', mail.outbox[0].subject)
        self.assertIn('newuser', mail.outbox[0].body)
        self.assertIn('newuser@example.com', mail.outbox[0].body)

        self.assertContains(response, 'Registration successful. Your account is pending approval.')

    def test_register_view_post_existing_user(self):
        # existing_user = User.objects.create_user(username='existinguser', email='existing@example.com', password='password')

        form_data = {
            'username': 'existinguser',
            'email': 'existing@example.com',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
        }
        response = self.client.post(reverse('register'), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

        self.assertContains(response, 'Username already exists. Please choose a different username.')

    def test_register_view_post_existing_email(self):
        # existing_user = User.objects.create_user(username='existinguser', email='existing@example.com', password='password')

        form_data = {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
        }
        response = self.client.post(reverse('register'), form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

        self.assertContains(response, 'Email address already exists. Please use a different email.')

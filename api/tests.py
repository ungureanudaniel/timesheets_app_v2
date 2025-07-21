from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User, Activity
from reports.models import MonthlyReport
from decimal import Decimal


class MonthlyReportAPITests(APITestCase):
    def setUp(self):
        # Create test users
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            username='testuser'
        )
        self.other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            username='otheruser'
        )

        # Create test activity
        self.activity = Activity.objects.create(
            name='Development',
            code='DEV'
        )

        # Create test report
        self.report = MonthlyReport.objects.create(
            user=self.user,
            activity=self.activity,
            description='API Development',
            timeframe='January 2023',
            date='2023-01-15',
            hours=Decimal('8.50')
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

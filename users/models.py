from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """
    Custom manager where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        # Normalize the email address
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)  # optional default
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class CustomUser(AbstractUser):
    """
    Custom user model that uses email as the unique identifier.
    """
    username = models.CharField(max_length=150, unique=False, blank=True)
    email = models.EmailField(_('email address'), unique=True, blank=False)
    is_approved = models.BooleanField(default=False)
    is_person = models.BooleanField(default=True)
    bio = models.TextField(default="Write a short description of yourself", blank=True)
    resume = models.FileField(upload_to='cv/', blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # only needed for createsuperuser

    objects = CustomUserManager()

    def __str__(self):
        return self.email or self.username

    def assign_initial_group(self):
        try:
            group, created = Group.objects.get_or_create(name='REPORTER')  # Ensure the group exists
            self.groups.add(group)  # Add user to the group
            logger.debug(f"Assigned {self.email} to group 'REPORTER'.")
        except Group.DoesNotExist:
            logger.error("Group 'REPORTER' does not exist.")

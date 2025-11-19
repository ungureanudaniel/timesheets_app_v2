from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
logger.info("Logging is set up.")

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


class CustomUser(AbstractUser):
    """
    Custom user model that uses email as the unique identifier.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField(max_length=150, unique=False, blank=True)
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    email = models.EmailField(_('email address'), unique=True, blank=False)
    is_approved = models.BooleanField(default=False)
    is_person = models.BooleanField(default=True)
    bio = models.TextField(default="Write a short description of yourself", blank=True)
    resume = models.FileField(upload_to='cv/', blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # only needed for createsuperuser

    objects = CustomUserManager()  # type: ignore[assignment]
    # Permissions
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="customuser_set",  # Add this line
        related_query_name="customuser",  # Add this line
    )
    # User Permissions
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="customuser_set",  # Add this line
        related_query_name="customuser",  # Add this line
    )

    @property
    def full_name(self):
        """Return the full name of the user"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    def get_full_name(self):
        """Official method for getting full name"""
        return self.full_name
    
    def assign_initial_group(self):
        try:
            group, created = Group.objects.get_or_create(name='REPORTER')  # Ensure the group exists
            self.groups.add(group)  # Add user to the group
            logger.debug(f"Assigned {self.email} to group 'REPORTER'.")
        except Group.DoesNotExist:
            logger.error("Group 'REPORTER' does not exist.")


    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    
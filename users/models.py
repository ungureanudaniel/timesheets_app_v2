from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class CustomUserManager(BaseUserManager):
    """
    Custom manager where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', CustomUser.Role.ADMIN)  # Auto-assign ADMIN role

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

    # Role field - CHOOSE ONE APPROACH: Either use this OR groups, not both
    class Role(models.TextChoices):
        REPORTER = 'REPORTER', _('Reporter')
        MANAGER = 'MANAGER', _('Manager')
        ADMIN = 'ADMIN', _('Admin')
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.REPORTER
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()

    # Groups and permissions (keep these for Django's permission system)
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="customuser_set",
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name="customuser_set",
        related_query_name="customuser",
    )

    @property
    def full_name(self):
        """Return the full name of the user"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    def get_full_name(self):
        """Official method for getting full name"""
        return self.full_name

    # Role properties - FIXED: Check both role field AND superuser status
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser
    
    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER
    
    @property
    def is_reporter(self):
        return self.role == self.Role.REPORTER and not self.is_superuser

    def assign_role_permissions(self):
        """
        Optional: Sync role field with groups for Django's permission system
        Use this if you want to use Django's group-based permissions alongside your role field
        """
        # Remove from all role groups
        self.groups.remove(*Group.objects.filter(name__in=['ADMIN', 'MANAGER', 'REPORTER']))
        
        # Add to role-specific group
        group, created = Group.objects.get_or_create(name=self.role)
        self.groups.add(group)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Auto-assign ADMIN role to superusers
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.role = self.Role.ADMIN
        
        super().save(*args, **kwargs)
        
        # Optional: Sync with groups for permission system
        self.assign_role_permissions()
        
        # Assign default REPORTER group to new regular users (optional)
        if is_new and not self.groups.exists() and self.role == self.Role.REPORTER:
            group, created = Group.objects.get_or_create(name='REPORTER')
            self.groups.add(group)

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name or self.last_name else self.email
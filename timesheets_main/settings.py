from pathlib import Path
import os
from dotenv import load_dotenv
from django.contrib.messages import constants as messages
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from mysql.connector.django.base import DatabaseWrapper

DatabaseWrapper.display_name = property(lambda self: "MySQL")

load_dotenv(verbose=True)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get("DEBUG", default=0))
ALLOWED_HOSTS = []
if os.getenv('ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend(os.getenv('ALLOWED_HOSTS').split(' '))

DEVELOPMENT = bool(os.environ.get("DEBUG", default=0))

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',  # message frmwk
    'django.contrib.staticfiles',
    'whitenoise.runserver_nostatic',
    # developer added libraries
    'django.contrib.sitemaps',
    'django.conf.urls.i18n',
    'hitcount',
    'tinymce',
    # 'django_recaptcha',
    # user apps
    'widget_tweaks',
    'general',
    'users',
    'reports',
    'dashboard',
    'timesheet',
    'api',
    'debug_toolbar',
    'axes',
]

# -----------authentication----------------------
AUTH_TOKEN_LENGTH = 100
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'users.auth_backend.EmailOrUsernameModelBackend',  # Your custom backend
    'django.contrib.auth.backends.ModelBackend',
]
AUTH_USER_MODEL = 'users.CustomUser'
# Axes Configuration
AXES_FAILURE_LIMIT = 5  # Lock after 5 failed attempts
AXES_COOLOFF_TIME = 1  # Lock for 1 hour
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = 'accounts/lockout.html'  # Create this template
AXES_VERBOSE = True  # Logging
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Development
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Production
# Optional: Customize lockout messages
AXES_LOCKOUT_PARAMETERS = ['username', 'ip_address']  # Lock by username only
AXES_RESET_COOL_OFF_ON_FAILURE = True
INTERNAL_IPS = [
    "127.0.0.1",
]

MIDDLEWARE = [
    # 'django.middleware.gzip.GZipMiddleware',
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    # --------caching middleware------------------
    # --------whitenoise middleware for media load
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # --------django internalization for language selection
    'django.contrib.messages.middleware.MessageMiddleware',  # message frmwk
    'django.middleware.common.CommonMiddleware',
    # --------caching middleware-------------------
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # -----------authentication---------------------
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'timesheets_main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',
            ],
        },
    },
]

WSGI_APPLICATION = 'timesheets_main.wsgi.application'

# Enable caching in project
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
        "LOCATION": "memcached:11211",
    }
}
# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'mysql.connector.django'),
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
        'OPTIONS': {
            'autocommit': True,
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

TIME_ZONE = 'Europe/Bucharest'

USE_I18N = True

USE_TZ = True

USE_L10N = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')
MEDIA_URL = '/media/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
SESSION_SAVE_EVERY_REQUEST = True

LANGUAGES = [
    ('en', _('English')),
    ('ro', _('Romanian')),
]
LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]
DEFAULT_LANGUAGE = 1
# Email configuration (for password resets)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'contact@bucegipark.ro')
ADMIN_URL = os.getenv('ADMIN_URL', 'https://www.bucegipark.ro/admin/')
ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', ['danielungureanu531@gmail.com'])
# ==============authentication settings=========================
SITE_ID = 1

# ==============EMAIL SETTINGS==========================
# -----test
# -----production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# -----email credentials
EMAIL_PORT = os.getenv('EMAIL_PORT')
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'contact@bucegipark.ro'
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
ACCOUNTANT_EMAIL = os.getenv('ACCOUNTANT_EMAIL')
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-secondary',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# ============ django-resized settings ====================
DJANGORESIZED_DEFAULT_SIZE = [1920, 1080]
DJANGORESIZED_DEFAULT_SCALE = 0.5
DJANGORESIZED_DEFAULT_QUALITY = 75
DJANGORESIZED_DEFAULT_KEEP_META = True
DJANGORESIZED_DEFAULT_FORCE_FORMAT = 'WebP'
DJANGORESIZED_DEFAULT_FORMAT_EXTENSIONS = {'WebP': ".WebP"}
DJANGORESIZED_DEFAULT_NORMALIZE_ROTATION = True
# ============ django-messages framework ====================
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

# ================django simple captcha======================
CAPTCHA_IMAGE_SIZE = (100, 50)
CAPTCHA_BACKGROUND_COLOR = "#2eb872"
CAPTCHA_FOREGROUND_COLOR = "black"
# ================django payments settings=====================
TICKET_EMAIL_HEADER = os.getenv('TICKET_EMAIL_HEADER')
BASE_URL = os.getenv('BASE_URL')
# =====================LOGGING  ERRORS=========================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'timesheets_main.log',
            'formatter': 'verbose'
        },
        'console': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'propagate': False,
            'level': 'ERROR',
        },
        'services': {
            'handlers': ['file'],
            'level': 'ERROR',
        },
        'payments': {
            'handlers': ['file'],
            'level': 'ERROR',
        },
    }
}
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

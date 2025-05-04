"""
Development settings for vital_tools project.
"""

from .base import *
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# SECURITY WARNING: keep the secret key used in development secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
    'factory_a': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'factory_a.sqlite3',
    },
    'factory_c': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'factory_c.sqlite3',
    }
}

# Additional development apps
INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
]

# Additional development middleware
MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

# Debug toolbar settings
INTERNAL_IPS = ['127.0.0.1']

# Email settings
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')

# Celery settings
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Celery Beat Configuration
CELERY_BEAT_SCHEDULE = {
    'periodic-sync': {
        'task': 'devices.services.sync.periodic_sync',
        'schedule': 120.0,  # Run every 2 minutes
    },
}

# Add database routers
DATABASE_ROUTERS = ['devices.routers.DataSourceRouter']

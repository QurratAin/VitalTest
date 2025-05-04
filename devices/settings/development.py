from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

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

# Database router
DATABASE_ROUTERS = ['devices.routers.DataSourceRouter'] 
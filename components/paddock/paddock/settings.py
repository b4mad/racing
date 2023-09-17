"""
Django settings for paddock project.
"""

import os
import sys
from pathlib import Path

import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False),
    LOGGING_DB_LEVEL=(str, "INFO"),
)

# Set the project base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

# False if not in os.environ because of casting above
DEBUG = env("DEBUG")

# True if testing
TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# Raises Django's ImproperlyConfigured
# exception if SECRET_KEY not in os.environ
SECRET_KEY = env("SECRET_KEY")

# https://github.com/korfuri/django-prometheus#monitoring-your-models
PROMETHEUS_EXPORT_MIGRATIONS = False

# PADDOCK_POD_IP might be set via kubernetes downward API
# https://kubernetes.io/docs/tasks/inject-data-application/environment-variable-expose-pod-information/
# and https://github.com/korfuri/django-prometheus/issues/81
# ALLOWED_HOST might be set via kubernetes deployment env
ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "paddock.b4mad.racing",
    os.environ.get("ALLOWED_HOST", ""),
    os.environ.get("PADDOCK_POD_IP", ""),
]


# Application definition
INSTALLED_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount.providers.openid",
    "allauth.socialaccount.providers.discord",
    "allauth.socialaccount.providers.github",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.microsoft",
    "allauth.socialaccount.providers.reddit",
    "allauth.socialaccount.providers.steam",
    "allauth.socialaccount.providers.twitch",
    "allauth.socialaccount",
    "bootstrap4",
    "fontawesomefree",
    "crispy_bootstrap4",
    "crispy_forms",
    "django_extensions",
    "django_plotly_dash.apps.DjangoPlotlyDashConfig",
    "django.contrib.admin",
    "django_admin_listfilter_dropdown",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "dpd_static_support",
    "explorer",
    "django_prometheus",
    "telemetry.apps.TelemetryConfig",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django_plotly_dash.middleware.BaseMiddleware",
    "django_plotly_dash.middleware.ExternalRedirectionMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "paddock.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, "paddock", "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
CRISPY_TEMPLATE_PACK = "bootstrap4"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"

WSGI_APPLICATION = "paddock.wsgi.application"

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

if TESTING:
    DATABASES = {
        "default": {
            "ENGINE": "django_prometheus.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        },
        "readonly": {
            "ENGINE": "django_prometheus.db.backends.sqlite3",
            "NAME": os.path.join(BASE_DIR, "db.sqlite3"),
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django_prometheus.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "paddock"),
            "USER": os.getenv("DB_USER", "paddock"),
            "PASSWORD": os.getenv("DB_PASSWORD", "paddock"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        },
        "readonly": {
            "ENGINE": "django_prometheus.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "paddock"),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", ""),
            "PORT": os.getenv("DB_PORT", "5432"),
        },
    }

# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

CSRF_TRUSTED_ORIGINS = ["https://*.b4mad.racing"]

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static/")
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django_plotly_dash.finders.DashAssetFinder",
    "django_plotly_dash.finders.DashComponentFinder",
    "django_plotly_dash.finders.DashAppDirectoryFinder",
]
STATICFILES_DIRS = [
    BASE_DIR / "paddock/assets/",
]

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "disable_existing_loggers": False,
    "version": 1,
    "formatters": {
        "timestamp": {
            "format": "{asctime} {levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            # logging handler that outputs log messages to terminal
            "class": "logging.StreamHandler",
            "level": "DEBUG",  # message level to be written to console
            "formatter": "timestamp",
        },
    },
    "loggers": {
        "": {
            # this sets root level logger to log debug and higher level
            # logs to console. All other loggers inherit settings from
            # root level logger.
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,  # this tells logger to send logging message
            # to its parent (will send if set to True)
        },
        "django.db": {
            # django also has database level logging
            "level": env("LOGGING_DB_LEVEL")
        },
    },
}

EXPLORER_CONNECTIONS = {"Default": "readonly"}
EXPLORER_DEFAULT_CONNECTION = "readonly"

# for plotly dash
X_FRAME_OPTIONS = "SAMEORIGIN"
PLOTLY_DASH = {
    # Route used for the message pipe websocket connection
    "ws_route": "dpd/ws/channel",
    # Route used for direct http insertion of pipe messages
    "http_route": "dpd/views",
    # Flag controlling existince of http poke endpoint
    "http_poke_enabled": True,
    # Insert data for the demo when migrating
    "insert_demo_migrations": False,
    # Timeout for caching of initial arguments in seconds
    "cache_timeout_initial_arguments": 60,
    # Name of view wrapping function
    "view_decorator": None,
    # Flag to control location of initial argument storage
    "cache_arguments": False,
    # Flag controlling local serving of assets
    "serve_locally": False,
}


# Plotly components containing static content that should
# be handled by the Django staticfiles infrastructure

PLOTLY_COMPONENTS = [
    # Common components (ie within dash itself) are automatically added
    # django-plotly-dash components
    "dpd_components",
    # static support if serving local assets
    "dpd_static_support",
    # Other components, as needed
    "dash_bootstrap_components",
]

# https://testdriven.io/blog/django-social-auth/
# https://dev.to/tylerlwsmith/styling-django-allauth-by-overriding-its-templates-3c31
AUTHENTICATION_BACKENDS = ("allauth.account.auth_backends.AuthenticationBackend",)
SITE_ID = 1
ACCOUNT_EMAIL_VERIFICATION = "none"
LOGIN_REDIRECT_URL = "home"
ACCOUNT_LOGOUT_ON_GET = True

# Provider specific settings
SOCIALACCOUNT_PROVIDERS = {
    "discord": {
        "APP": {
            "client_id": os.getenv("SOCIALACCOUNT_DISCORD_CLIENTID", ""),
            "secret": os.getenv("SOCIALACCOUNT_DISCORD_SECRET", ""),
            "key": "",
        }
    },
    "github": {
        "APP": {
            "client_id": os.getenv("SOCIALACCOUNT_GITHUB_CLIENTID", ""),
            "secret": os.getenv("SOCIALACCOUNT_GITHUB_SECRET", ""),
            "key": "",
        }
    },
    "reddit": {
        "APP": {
            "client_id": os.getenv("SOCIALACCOUNT_REDDIT_CLIENTID", ""),
            "secret": os.getenv("SOCIALACCOUNT_REDDIT_SECRET", ""),
            "key": "",
        }
    },
    "steam": {
        "APP": {
            "client_id": os.getenv("SOCIALACCOUNT_STEAM_KEY", ""),
            "secret": os.getenv("SOCIALACCOUNT_STEAM_KEY", ""),
            "key": "",
        }
    },
    "microsoft": {
        "APP": {
            "client_id": os.getenv("SOCIALACCOUNT_MICROSOFT_CLIENTID", ""),
            "secret": os.getenv("SOCIALACCOUNT_MICROSOFT_SECRET", ""),
            "key": "",
        }
    },
    "google": {
        "APP": {
            "client_id": os.getenv("SOCIALACCOUNT_GOOGLE_CLIENTID", ""),
            "secret": os.getenv("SOCIALACCOUNT_GOOGLE_SECRET", ""),
            "key": "",
        }
    },
}

sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn and sentry_dsn.startswith("http"):
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[DjangoIntegration()],
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        send_default_pii=True,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )

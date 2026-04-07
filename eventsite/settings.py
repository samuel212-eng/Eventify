# =============================================
#  Settings — the "control panel" for our site
# =============================================

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Keep this secret before going live!
SECRET_KEY = 'django-insecure-change-me-before-going-live-abc123xyz'

# True = helpful error pages while building
DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',        # Built-in admin panel
    'django.contrib.auth',         # Login / logout / users
    'django.contrib.contenttypes',
    'django.contrib.sessions',     # Remembers who is logged in
    'django.contrib.messages',     # Flash messages ("Event saved!")
    'django.contrib.staticfiles',  # CSS / JS files
    'events',                      # OUR app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'eventsite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],   # Our global HTML folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'eventsite.wsgi.application'

# Simple file-based database — no installation needed
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# After login → go home. After logout → go to login page.
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'

# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Eventify <noreply@eventify.co.ke>'
# # ── FEATURE 3: Email settings ──────────────
# #
# # During development — emails print to your terminal (no SMTP needed)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

#When you're ready to send real emails, swap to Gmail:
EMAIL_BACKEND   = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST      = 'smtp.gmail.com'
EMAIL_PORT      = 587
EMAIL_USE_TLS   = True
EMAIL_HOST_USER = 'samstorm855@gmail.com'
EMAIL_HOST_PASSWORD = 'tffm fpyp rktq xpxp'   # Google App Password, NOT your real password

DEFAULT_FROM_EMAIL = 'Eventify <noreply@eventify.co.ke>'

# # ── ADMIN DASHBOARD: your email ─────────────
ADMIN_EMAIL = 'admin@eventify.co.ke'



# Your app's Consumer Key and Consumer Secret
MPESA_CONSUMER_KEY    = 'HvzHVkFsU09KnLAxH5zTzM6A1RQ6pffq3k6OIALmdJ8jfA1G'
MPESA_CONSUMER_SECRET = '8AO37Y4jgjaj0RYzakTAd4jXKhHnfJLmi9bcsq99hoAbAxRztrZA08ovh01VrrQL'

# Default sandbox shortcode is 174379
MPESA_SHORTCODE = '174379'

MPESA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'

# Example: https://abc123.ngrok.io/mpesa/callback/
MPESA_CALLBACK_URL = 'https://sandbox.safaricom.co.ke/mpesa/callback/'

# Switch to 'live' when going to production

MPESA_ENV = 'sandbox'



PAYPAL_CLIENT_ID = 'your_client_id_here'
PAYPAL_SECRET    = 'your_secret_here'
PAYPAL_BASE_URL  = 'https://api-m.sandbox.paypal.com'

# ai key
ANTHROPIC_API_KEY = 'your-key-from-console.anthropic.com'
# =============================================
#  Paste these at the BOTTOM of settings.py
# =============================================

# ── FEATURE 3: Email settings ──────────────
#
# During development — emails print to your terminal (no SMTP needed)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# When you're ready to send real emails, swap to Gmail:
# EMAIL_BACKEND   = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST      = 'smtp.gmail.com'
# EMAIL_PORT      = 587
# EMAIL_USE_TLS   = True
# EMAIL_HOST_USER = 'your@gmail.com'
# EMAIL_HOST_PASSWORD = 'your_app_password'   # Google App Password, NOT your real password

DEFAULT_FROM_EMAIL = 'Eventify <noreply@eventify.co.ke>'

# ── ADMIN DASHBOARD: your email ─────────────
ADMIN_EMAIL = 'admin@eventify.co.ke'

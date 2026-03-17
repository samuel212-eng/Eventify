"""
SETUP INSTRUCTIONS FOR ALL 7 NEW FEATURES
Run these commands in your terminal after unzipping the project.
"""

STEPS = """
==============================================
  STEP 1 — Run database migrations
  (creates tables for new models: EventReview, Waitlist, and new Registration fields)
==============================================

    python manage.py makemigrations
    python manage.py migrate


==============================================
  STEP 2 — Add email setting to settings.py
==============================================

Paste this at the bottom of eventsite/settings.py:

    EMAIL_BACKEND  = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'Eventify <noreply@eventify.co.ke>'

This makes emails print to your terminal during development.
No SMTP setup needed yet.


==============================================
  STEP 3 — Check the admin dashboard URL
==============================================

Visit:  http://127.0.0.1:8000/dashboard/
(You must be logged in as a staff user)

To make your user a staff user, run:
    python manage.py shell
    >>> from django.contrib.auth.models import User
    >>> u = User.objects.get(username='your_username')
    >>> u.is_staff = True
    >>> u.save()


==============================================
  SUMMARY OF ALL NEW URLS
==============================================

Feature 1 — Reviews
  POST  /events/<pk>/review/          Submit a review
  GET   /reviews/<pk>/delete/         Delete your review

Feature 2 — Attendee Badge
  (automatic — shown on event detail page, no new URL)

Feature 3 — Email Confirmation
  (automatic — fires when someone registers, no new URL)

Feature 4 — Admin Dashboard
  GET   /dashboard/                   Admin analytics page

Feature 5 — Waitlist
  GET   /events/<pk>/waitlist/join/   Join the waitlist
  POST  /events/<pk>/waitlist/leave/  Leave the waitlist

Feature 6 — Check-In System
  GET   /events/<pk>/checkin/         Check-in dashboard (organiser only)
  POST  /events/<pk>/checkin/code/    Check in by code (AJAX)
  POST  /checkin/manual/<pk>/         Manual check-in click (AJAX)

Feature 7 — Progress Bar
  (automatic — shown on event detail page, no new URL)
"""

print(STEPS)

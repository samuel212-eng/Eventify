# =============================================
#  INSTRUCTIONS — what to add/change
# =============================================

# -------------------------------------------
# 1. ADD THESE URLS to events/urls.py
# -------------------------------------------
URLS_TO_ADD = """
from . import verification_views

# Organiser verification
path('verify/',                         verification_views.apply_for_verification,   name='apply_for_verification'),
path('verify/pending/',                 verification_views.verification_pending,      name='verification_pending'),

# Report an event
path('events/<int:event_pk>/report/',   verification_views.report_event,             name='report_event'),

# Admin views (staff only)
path('admin-panel/verifications/',      verification_views.admin_verification_queue,  name='admin_verification_queue'),
path('admin-panel/verify/<int:profile_id>/', verification_views.admin_review_organiser, name='admin_review_organiser'),
path('admin-panel/events/',             verification_views.admin_event_approval_queue, name='admin_event_approval_queue'),
path('admin-panel/events/<int:approval_id>/', verification_views.admin_review_event,   name='admin_review_event'),
"""

# -------------------------------------------
# 2. ADD THIS TO event_detail.html
#    in the organiser info box section
# -------------------------------------------
VERIFIED_BADGE_HTML = """
{% load verification_tags %}
{% if event.organizer|is_verified_organizer %}
  <div style="
    display:inline-flex; align-items:center; gap:.4rem;
    background:rgba(25,200,120,.1); border:1px solid rgba(25,200,120,.3);
    border-radius:50px; padding:.3rem .9rem; margin-top:.5rem;
    font-size:.8rem; font-weight:600; color:#19C878;
  ">
    <i class="bi bi-shield-check-fill"></i> Verified Organiser
  </div>
{% endif %}
"""

# -------------------------------------------
# 3. ADD THIS to event_detail.html
#    below the action buttons area
# -------------------------------------------
REPORT_BUTTON_HTML = """
<div style="text-align:center; margin-top:1.5rem;">
  <a href="{% url 'report_event' event.pk %}"
     style="color:var(--muted); font-size:.78rem; text-decoration:none;">
    <i class="bi bi-flag me-1"></i>Report this event
  </a>
</div>
"""

# -------------------------------------------
# 4. ADD THIS TEMPLATE TAG to display the badge
#    Create: events/templatetags/__init__.py (empty)
#    Create: events/templatetags/verification_tags.py
# -------------------------------------------
TEMPLATE_TAG = """
# events/templatetags/verification_tags.py

from django import template
from events.models import OrganizerProfile

register = template.Library()

@register.filter
def is_verified_organizer(user):
    # Returns True if this user is a verified organiser
    try:
        return user.organizer_profile.is_verified
    except OrganizerProfile.DoesNotExist:
        return False
"""

print("Read the INSTRUCTIONS sections above and apply each one.")

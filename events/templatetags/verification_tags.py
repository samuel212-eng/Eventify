# events/templatetags/verification_tags.py
from django import template
from events.models import OrganizerProfile   # <-- from models, not verification_models

register = template.Library()

@register.filter
def is_verified_organizer(user):
    try:
        return user.organizer_profile.is_verified
    except OrganizerProfile.DoesNotExist:
        return False

@register.filter
def verification_status(user):
    try:
        return user.organizer_profile.status
    except OrganizerProfile.DoesNotExist:
        return 'unverified'

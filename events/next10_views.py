# events/next10_views.py
# =============================================
#  Views for the Next 10 medium-impact features:
#  11. Follow Organiser
#  12. Countdown timer (handled in template)
#  13. "X people viewing now" (handled in template JS)
#  14. Category chip bar (handled in template)
#  15. Live exchange rate for PayPal
#  16. WhatsApp share (handled in card template)
#  17. Featured large card (handled in template)
#  18. Organiser profile page with stats
#  19. Consistent spacing (CSS only)
#  20. Save / Bookmark events
# =============================================

import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.core.paginator import Paginator

from .models import Event, Registration, EventReview, OrganizerFollow, SavedEvent


# ─────────────────────────────────────────────
#  FEATURE 11: FOLLOW / UNFOLLOW ORGANISER
# ─────────────────────────────────────────────

@login_required
def follow_organizer(request, username):
    """Toggle follow/unfollow for an organiser"""
    organizer = get_object_or_404(User, username=username)

    # Can't follow yourself
    if organizer == request.user:
        messages.error(request, "You can't follow yourself.")
        return redirect('organiser_profile', username=username)

    follow, created = OrganizerFollow.objects.get_or_create(
        follower  = request.user,
        organizer = organizer,
    )

    if not created:
        # Already following — unfollow
        follow.delete()
        messages.success(request, f"You unfollowed {organizer.username}.")
    else:
        messages.success(request, f"✅ You're now following {organizer.username}! You'll be notified when they create new events.")

    return redirect('organiser_profile', username=username)


# ─────────────────────────────────────────────
#  FEATURE 15: LIVE EXCHANGE RATE
# ─────────────────────────────────────────────

def get_usd_rate():
    """
    Fetch live KES→USD rate from a free API.
    Falls back to 130 if the API is unavailable.
    """
    try:
        response = requests.get(
            'https://api.frankfurter.app/latest?from=KES&to=USD',
            timeout=3,
        )
        data = response.json()
        return data['rates']['USD']
    except Exception:
        return 1 / 130   # fallback: 1 KES = 1/130 USD


# ─────────────────────────────────────────────
#  FEATURE 18: ORGANISER PUBLIC PROFILE
# ─────────────────────────────────────────────

def organiser_profile(request, username):
    """
    Public profile page for an event organiser.
    Shows: bio, total events, total attendees, rating, events list.
    """
    organiser = get_object_or_404(User, username=username)
    events    = Event.objects.filter(organizer=organiser, is_published=True).order_by('-date')

    # Stats
    total_events    = events.count()
    total_attendees = sum(e.spots_taken() for e in events)

    # Average rating across all their events
    all_reviews = EventReview.objects.filter(event__organizer=organiser)
    avg_rating  = all_reviews.aggregate(avg=Avg('rating'))['avg']
    avg_rating  = round(avg_rating, 1) if avg_rating else None
    total_reviews = all_reviews.count()

    # Is the logged-in user following this organiser?
    is_following = False
    if request.user.is_authenticated and request.user != organiser:
        is_following = OrganizerFollow.objects.filter(
            follower  = request.user,
            organizer = organiser,
        ).exists()

    # Follower count
    follower_count = OrganizerFollow.objects.filter(organizer=organiser).count()

    # Paginate their events
    paginator = Paginator(events, 6)
    page      = request.GET.get('page', 1)
    events    = paginator.get_page(page)

    return render(request, 'events/organiser_profile.html', {
        'organiser':       organiser,
        'events':          events,
        'total_events':    total_events,
        'total_attendees': total_attendees,
        'avg_rating':      avg_rating,
        'total_reviews':   total_reviews,
        'is_following':    is_following,
        'follower_count':  follower_count,
    })


# ─────────────────────────────────────────────
#  FEATURE 20: SAVE / BOOKMARK EVENTS
# ─────────────────────────────────────────────

@login_required
def toggle_save_event(request, event_pk):
    """Save or unsave an event. Returns JSON for AJAX calls."""
    event = get_object_or_404(Event, pk=event_pk)

    saved, created = SavedEvent.objects.get_or_create(
        user  = request.user,
        event = event,
    )

    if not created:
        saved.delete()
        return JsonResponse({'saved': False,  'message': 'Removed from saved events'})
    else:
        return JsonResponse({'saved': True,   'message': '❤️ Event saved!'})


@login_required
def saved_events(request):
    """Page showing all events a user has saved"""
    saves = SavedEvent.objects.filter(
        user=request.user
    ).select_related('event').order_by('-saved_at')

    return render(request, 'events/saved_events.html', {'saves': saves})


# ─────────────────────────────────────────────
#  "X PEOPLE VIEWING NOW" — simulated
# ─────────────────────────────────────────────

def viewers_count(request, event_pk):
    """
    Returns a realistic 'X people viewing now' number.
    In production: use Redis to track real sessions per event.
    Here: we simulate based on event popularity + random variance.
    """
    import random
    event = get_object_or_404(Event, pk=event_pk)

    # Base count on registrations (more registrations = more viewers)
    base = max(2, event.spots_taken() // 3)
    # Add some randomness so it looks live
    count = base + random.randint(1, 8)

    return JsonResponse({'viewers': count})

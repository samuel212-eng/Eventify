# Add to events/extra_views.py or create events/dashboard_views.py

import json
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q

from .models import Event, Registration, EventReview


@login_required
def organiser_dashboard(request, event_pk):
    """
    Full organiser analytics dashboard.
    Polished version with check-in analytics, revenue, rating breakdown.
    """
    event = get_object_or_404(Event, pk=event_pk)

    if event.organizer != request.user:
        messages.error(request, "Only the event organiser can view this dashboard.")
        return redirect('event_detail', slug=event.slug)

    registrations = Registration.objects.filter(event=event).select_related('user')
    total_regs    = registrations.count()
    checked_in    = registrations.filter(checked_in=True).count()
    no_show       = total_regs - checked_in
    checkin_rate  = round((checked_in / total_regs * 100) if total_regs else 0, 1)
    total_revenue = float(event.price) * total_regs

    # Page views
    total_views     = sum(pv.view_count for pv in event.page_views.all()) if hasattr(event, 'page_views') else 0
    conversion_rate = round((total_regs / total_views * 100) if total_views else 0, 1)

    # Registrations per day — last 14 days
    today      = timezone.now().date()
    reg_by_day = {}
    for i in range(13, -1, -1):
        day = today - datetime.timedelta(days=i)
        reg_by_day[day.strftime('%b %d')] = 0

    for reg in registrations:
        day_str = reg.registered_at.date().strftime('%b %d')
        if day_str in reg_by_day:
            reg_by_day[day_str] += 1

    chart_labels = json.dumps(list(reg_by_day.keys()))
    chart_data   = json.dumps(list(reg_by_day.values()))

    # Reviews and rating breakdown
    reviews    = event.reviews.all()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    avg_rating = round(avg_rating, 1) if avg_rating else None
    review_count = reviews.count()

    # Rating breakdown as percentages
    rating_breakdown = []
    for star in [5, 4, 3, 2, 1]:
        count = reviews.filter(rating=star).count()
        pct   = round((count / review_count * 100) if review_count else 0)
        rating_breakdown.append((star, pct))

    # Recent 8 registrations
    recent_registrations = registrations.order_by('-registered_at')[:8]

    # Waitlist
    waitlist_count = 0
    if hasattr(event, 'waitlist'):
        waitlist_count = event.waitlist.count()

    return render(request, 'events/organiser_dashboard.html', {
        'event':                event,
        'total_regs':           total_regs,
        'checked_in':           checked_in,
        'no_show':              no_show,
        'checkin_rate':         checkin_rate,
        'total_revenue':        total_revenue,
        'total_views':          total_views,
        'conversion_rate':      conversion_rate,
        'chart_labels':         chart_labels,
        'chart_data':           chart_data,
        'avg_rating':           avg_rating,
        'review_count':         review_count,
        'rating_breakdown':     rating_breakdown,
        'recent_registrations': recent_registrations,
        'waitlist_count':       waitlist_count,
    })

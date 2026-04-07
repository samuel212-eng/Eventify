# events/extra_views.py
#  Views for:
#  - PDF ticket download (handled in pdf_views.py)
#  - Promo codes
#  - Notifications
#  - Event Q&A
#  - Organiser analytics
#  - Search autocomplete
#  - Review reply
#  - Page view tracking

import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.views.decorators.http import require_POST

from .models import (
    Event, Registration, EventReview, EventQuestion,
    Notification, EventPageView, ReviewReply
)



#  PROMO CODE VALIDATION (AJAX endpoint)


def validate_promo_code(request, event_pk):
    """
    Called by JavaScript when user types a promo code at checkout.
    Returns the discounted price as JSON.
    """
    from .models import PromoCode   # import after adding to models.py

    event = get_object_or_404(Event, pk=event_pk)
    code  = request.GET.get('code', '').strip().upper()

    if not code:
        return JsonResponse({'valid': False, 'error': 'Please enter a code.'})

    try:
        promo = PromoCode.objects.get(code=code, event=event)
    except PromoCode.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Code not found for this event.'})

    is_valid, reason = promo.is_valid()
    if not is_valid:
        return JsonResponse({'valid': False, 'error': reason})

    discounted = promo.calculate_discount(event.price)
    saving     = event.price - discounted

    return JsonResponse({
        'valid':      True,
        'original':   str(event.price),
        'discounted': str(discounted),
        'saving':     str(saving),
        'message':    f'🎉 Code applied! You save KES {saving:.0f}',
    })


#  NOTIFICATIONS


@login_required
def notification_list(request):
    """Full notifications page"""
    notifs = Notification.objects.filter(user=request.user)
    # Mark all as read when page is opened
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'events/notifications.html', {'notifications': notifs[:50]})


@login_required
def notification_count(request):
    """AJAX: returns unread count for the navbar bell"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


@login_required
def mark_notification_read(request, notif_pk):
    """Mark a single notification as read"""
    notif = get_object_or_404(Notification, pk=notif_pk, user=request.user)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect('notification_list')


def create_notification(user, notif_type, title, message, link=''):
    """
    Helper function — call this anywhere you want to create a notification.
    Example: create_notification(event.organizer, 'new_registration',
                '🎟️ New registration', f'{user.username} just registered for {event.title}',
                f'/events/{event.slug}/')
    """
    Notification.objects.create(
        user       = user,
        notif_type = notif_type,
        title      = title,
        message    = message,
        link       = link,
    )


#  EVENT Q&A


@login_required
@require_POST
def ask_question(request, event_pk):
    """User submits a question about an event"""
    event    = get_object_or_404(Event, pk=event_pk)
    question = request.POST.get('question', '').strip()

    if len(question) < 5:
        messages.error(request, "Please write a more detailed question.")
        return redirect('event_detail', slug=event.slug)

    EventQuestion.objects.create(
        event    = event,
        author   = request.user,
        question = question,
    )

    # Notify the organiser
    create_notification(
        user       = event.organizer,
        notif_type = 'new_registration',
        title      = f'New question on {event.title}',
        message    = f'{request.user.username} asked: "{question[:80]}"',
        link       = f'/events/{event.slug}/#qa',
    )

    messages.success(request, "✅ Your question has been posted! The organiser will answer it soon.")
    return redirect('event_detail', slug=event.slug)


@login_required
@require_POST
def answer_question(request, question_pk):
    """Organiser answers a question"""
    q     = get_object_or_404(EventQuestion, pk=question_pk)
    event = q.event

    if event.organizer != request.user:
        messages.error(request, "Only the event organiser can answer questions.")
        return redirect('event_detail', slug=event.slug)

    answer = request.POST.get('answer', '').strip()
    if not answer:
        messages.error(request, "Please write an answer.")
        return redirect('event_detail', slug=event.slug)

    q.answer      = answer
    q.answered_by = request.user
    q.answered_at = timezone.now()
    q.save()

    # Notify the person who asked
    create_notification(
        user       = q.author,
        notif_type = 'new_review',
        title      = f'Your question was answered!',
        message    = f'{event.organizer.username} answered your question about {event.title}',
        link       = f'/events/{event.slug}/#qa',
    )

    messages.success(request, "✅ Answer posted!")
    return redirect('event_detail', slug=event.slug)


#  REVIEW REPLY


@login_required
@require_POST
def reply_to_review(request, review_pk):
    """Organiser replies to a review publicly"""
    review = get_object_or_404(EventReview, pk=review_pk)

    if review.event.organizer != request.user:
        messages.error(request, "Only the event organiser can reply to reviews.")
        return redirect('event_detail', slug=review.event.slug)

    # Only one reply per review
    if hasattr(review, 'reply'):
        messages.warning(request, "You've already replied to this review.")
        return redirect('event_detail', slug=review.event.slug)

    reply_text = request.POST.get('reply', '').strip()
    if not reply_text:
        messages.error(request, "Please write a reply.")
        return redirect('event_detail', slug=review.event.slug)

    ReviewReply.objects.create(
        review  = review,
        author  = request.user,
        message = reply_text,
    )

    messages.success(request, "✅ Reply posted!")
    return redirect('event_detail', slug=review.event.slug)


#  ORGANISER ANALYTICS

@login_required
def organiser_analytics(request, event_pk):
    """
    Per-event analytics dashboard visible only to the organiser.
    Shows: page views, registrations over time, revenue, check-in rate.
    """
    event = get_object_or_404(Event, pk=event_pk)

    if event.organizer != request.user:
        messages.error(request, "Only the organiser can view analytics.")
        return redirect('event_detail', slug=event.slug)

    registrations   = Registration.objects.filter(event=event)
    total_regs      = registrations.count()
    checked_in      = registrations.filter(checked_in=True).count()
    checkin_rate    = round((checked_in / total_regs * 100) if total_regs else 0, 1)

    # Total revenue
    total_revenue   = float(event.price) * total_regs

    # Page views — total across all days
    total_views     = sum(pv.view_count for pv in event.page_views.all())

    # Conversion rate: (registrations / page views) × 100
    conversion_rate = round((total_regs / total_views * 100) if total_views else 0, 1)

    # Daily registrations for chart (last 14 days)
    import datetime
    today           = timezone.now().date()
    reg_by_day      = {}
    for i in range(13, -1, -1):
        day = today - datetime.timedelta(days=i)
        reg_by_day[day.strftime('%b %d')] = 0

    for reg in registrations.all():
        day_str = reg.registered_at.date().strftime('%b %d')
        if day_str in reg_by_day:
            reg_by_day[day_str] += 1

    chart_labels = list(reg_by_day.keys())
    chart_data   = list(reg_by_day.values())

    # Reviews summary
    reviews      = event.reviews.all()
    avg_rating   = reviews.aggregate(avg=Avg('rating'))['avg']
    avg_rating   = round(avg_rating, 1) if avg_rating else None

    return render(request, 'events/organiser_analytics.html', {
        'event':           event,
        'total_regs':      total_regs,
        'checked_in':      checked_in,
        'checkin_rate':    checkin_rate,
        'total_revenue':   total_revenue,
        'total_views':     total_views,
        'conversion_rate': conversion_rate,
        'chart_labels':    json.dumps(chart_labels),
        'chart_data':      json.dumps(chart_data),
        'avg_rating':      avg_rating,
        'review_count':    reviews.count(),
        'spots_left':      event.spots_left(),
    })


#  PAGE VIEW TRACKER

def track_page_view(event):
    """
    Call this inside event_detail view to track visits.
    Increments today's count or creates a new row.
    """
    today = timezone.now().date()
    obj, created = EventPageView.objects.get_or_create(
        event=event,
        date=today,
        defaults={'view_count': 1}
    )
    if not created:
        # Use F() expression to avoid race conditions
        from django.db.models import F
        EventPageView.objects.filter(pk=obj.pk).update(view_count=F('view_count') + 1)


#  SEARCH AUTOCOMPLETE


def search_autocomplete(request):
    """
    AJAX endpoint for search suggestions.
    Returns up to 6 matching event titles as JSON.
    Called by the search box as the user types.
    """
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return JsonResponse({'results': []})

    events = Event.objects.filter(
        is_published=True,
    ).filter(
        Q(title__icontains=query) |
        Q(location__icontains=query) |
        Q(category__name__icontains=query)
    ).values('title', 'slug', 'date', 'price')[:6]

    results = []
    for e in events:
        results.append({
            'title':    e['title'],
            'slug':     e['slug'],
            'date':     e['date'].strftime('%b %d, %Y') if e['date'] else '',
            'price':    'Free' if e['price'] == 0 else f"KES {e['price']:.0f}",
            'url':      f"/events/{e['slug']}/",
        })

    return JsonResponse({'results': results})


#  COPY LINK (log it, return the URL)


def get_event_share_link(request, event_pk):
    """Returns the full shareable URL for an event"""
    event = get_object_or_404(Event, pk=event_pk)
    url   = request.build_absolute_uri(f'/events/{event.slug}/')
    return JsonResponse({'url': url})



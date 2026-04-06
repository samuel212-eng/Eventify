# events/feature_views.py
#  Views for all 7 new features.
#  Import these in your events/urls.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Avg
from django.core.mail import send_mail
from django.conf import settings

from fix import event
from .models import Event, Registration, EventReview, Waitlist

import qrcode
import io
import csv
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage



# ═══════════════════════════════════════════
#  FEATURE 1 — REVIEWS
# ═══════════════════════════════════════════

@login_required
def submit_review(request, event_pk):
    """
    POST-only view. The review form lives on the event detail page.
    We process it here and redirect back.
    """
    event = get_object_or_404(Event, pk=event_pk)

    # Only registered attendees can review
    if not Registration.objects.filter(event=event, user=request.user).exists():
        messages.error(request, "You can only review events you attended.")
        return redirect('event_detail', slug=event.slug)

    # Only one review per person
    if EventReview.objects.filter(event=event, author=request.user).exists():
        messages.warning(request, "You've already reviewed this event.")
        return redirect('event_detail',slug=event.slug )

    if request.method == 'POST':
        rating  = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()

        # Validate
        if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
            messages.error(request, "Please choose a rating between 1 and 5.")
            return redirect('event_detail', slug=event.slug)

        if len(comment) < 10:
            messages.error(request, "Please write at least 10 characters.")
            return redirect('event_detail', slug=event.slug)

        EventReview.objects.create(
            event   = event,
            author  = request.user,
            rating  = int(rating),
            comment = comment,
        )
        messages.success(request, "✅ Your review has been posted!")

    return redirect('event_detail', slug=event.slug)


@login_required
def delete_review(request, review_pk):
    """Only the author can delete their review"""
    review = get_object_or_404(EventReview, pk=review_pk, author=request.user)
    event_pk = review.event.pk
    review.delete()
    messages.success(request, "Review deleted.")
    return redirect('event_detail', slug=event.slug)


# ═══════════════════════════════════════════
#  FEATURE 3 — EMAIL CONFIRMATION
#  (called automatically inside event_register view)
# ═══════════════════════════════════════════


def send_registration_confirmation(user, event, registration):
    subject = f"🎟️ You're registered: {event.title}"

    text_message = f"""
Hi {user.first_name or user.username},

Great news — you're officially registered for:

  📅 {event.title}
  📆 {event.date.strftime('%A, %B %d, %Y at %I:%M %p')}
  📍 {event.location}

Your check-in code: {registration.check_in_code}
Your QR code is attached — show it at the door.

{'This event is FREE.' if event.price == 0 else f'Amount paid: KES {event.price}'}

See you there!
— The Eventify Team
    """.strip()

    html_message = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:20px;">
      <h2 style="color:#3A86FF;">🎟️ You're registered!</h2>
      <p>Hi {user.first_name or user.username},</p>
      <p>Great news — you're officially registered for:</p>

      <div style="background:#f5f5f5;border-radius:10px;padding:16px;margin:16px 0;">
        <strong style="font-size:1.1rem;">{event.title}</strong><br><br>
        📆 {event.date.strftime('%A, %B %d, %Y at %I:%M %p')}<br>
        📍 {event.location}<br><br>
        {'🆓 This event is FREE.' if event.price == 0 else f'💳 Amount paid: KES {event.price}'}
      </div>

      <p>Your check-in code:</p>
      <div style="background:#3A86FF;color:#fff;font-size:1.6rem;font-weight:700;letter-spacing:4px;
                  text-align:center;padding:16px;border-radius:10px;margin:8px 0;">
        {registration.check_in_code}
      </div>

      <p style="text-align:center;color:#555;">Show this QR code at the door:</p>
      <img src="cid:qrcode" style="width:200px;height:200px;display:block;margin:16px auto;border-radius:10px;">

      <p style="color:#999;font-size:.8rem;text-align:center;margin-top:24px;">
        See you there! — The Eventify Team
      </p>
    </div>
    """

    # Generate QR code
    qr = qrcode.make(registration.check_in_code)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    buffer.seek(0)

    # Build email
    email = EmailMultiAlternatives(
        subject    = subject,
        body       = text_message,
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eventify.co.ke'),
        to         = [user.email],
    )
    email.attach_alternative(html_message, "text/html")

    # Attach QR code inline
    qr_image = MIMEImage(buffer.read())
    qr_image.add_header('Content-ID', '<qrcode>')
    qr_image.add_header('Content-Disposition', 'inline', filename='checkin_qr.png')
    email.attach(qr_image)

    email.send(fail_silently=True)

def send_waitlist_notification(user, event):
    # Get their registration check-in code
    registration = Registration.objects.get(event=event, user=user)

    subject = f"🎉 You're in! – {event.title}"

    text_message = f"""
Hi {user.first_name or user.username},

Great news! A spot just opened up and you've been automatically registered for:

  📅 {event.title}
  📆 {event.date.strftime('%A, %B %d, %Y at %I:%M %p')}
  📍 {event.location}

Your check-in code: {registration.check_in_code}
Your QR code is attached — show it at the door.

— The Eventify Team
    """.strip()

    html_message = f"""
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:20px;">
      <h2 style="color:#3A86FF;">🎉 You're registered!</h2>
      <p>Hi {user.first_name or user.username},</p>
      <p>A spot opened up and you've been automatically registered for:</p>
      <div style="background:#f5f5f5;border-radius:10px;padding:16px;margin:16px 0;">
        <strong>{event.title}</strong><br>
        📆 {event.date.strftime('%A, %B %d, %Y at %I:%M %p')}<br>
        📍 {event.location}
      </div>
      <p>Your check-in code: <strong style="font-size:1.4rem;letter-spacing:3px;">{registration.check_in_code}</strong></p>
      <p>Show the QR code below at the door:</p>
      <img src="cid:qrcode" style="width:200px;height:200px;display:block;margin:16px auto;">
      <p style="color:#999;font-size:.8rem;text-align:center;">— The Eventify Team</p>
    </div>
    """

    # Generate QR code from check-in code
    qr = qrcode.make(registration.check_in_code)
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    buffer.seek(0)

    # Build email
    email = EmailMultiAlternatives(
        subject       = subject,
        body          = text_message,
        from_email    = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eventify.co.ke'),
        to            = [user.email],
    )
    email.attach_alternative(html_message, "text/html")

    # Attach QR code image inline
    qr_image = MIMEImage(buffer.read())
    qr_image.add_header('Content-ID', '<qrcode>')
    qr_image.add_header('Content-Disposition', 'inline', filename='checkin_qr.png')
    email.attach(qr_image)

    email.send(fail_silently=True)

# ═══════════════════════════════════════════
#  FEATURE 5 — WAITLIST
# ═══════════════════════════════════════════

@login_required
def join_waitlist(request, event_pk):
    """Add the current user to the event's waitlist"""
    event = get_object_or_404(Event, pk=event_pk, is_published=True)

    # Already registered? No need for waitlist
    if Registration.objects.filter(event=event, user=request.user).exists():
        messages.info(request, "You're already registered for this event!")
        return redirect('event_detail', slug=event.slug)

    # Already on the waitlist?
    if Waitlist.objects.filter(event=event, user=request.user).exists():
        messages.warning(request, "You're already on the waitlist.")
        return redirect('event_detail', slug=event.slug)

    # Event must actually be full to join waitlist
    if not event.is_full():
        messages.info(request, "This event still has spots. Register directly!")
        return redirect('event_register', pk=event_pk)

    entry = Waitlist.objects.create(event=event, user=request.user)

    messages.success(request,
        f"You're #{entry.position()} on the waitlist. "
        "We'll email you if a spot opens up."
    )
    return redirect('event_detail', slug=event.slug)


@login_required
def leave_waitlist(request, event_pk):
    """Remove the current user from the waitlist"""
    event = get_object_or_404(Event, pk=event_pk)
    entry = get_object_or_404(Waitlist, event=event, user=request.user)

    if request.method == 'POST':
        entry.delete()
        messages.success(request, "You've been removed from the waitlist.")
        return redirect('event_detail', slug=event.slug)

    return render(request, 'events/leave_waitlist_confirm.html', {'event': event})


def notify_next_on_waitlist(event):
    next_entry = Waitlist.objects.filter(
        event=event,
        notified_at__isnull=True
    ).first()

    if next_entry:
        # Actually register them
        Registration.objects.get_or_create(
            event=event,
            user=next_entry.user,
        )
        # Remove from waitlist
        next_entry.delete()
        # Notify them
        send_waitlist_notification(next_entry.user, event)

# ═══════════════════════════════════════════
#  FEATURE 6 — CHECK-IN SYSTEM
# ═══════════════════════════════════════════

@login_required
def checkin_dashboard(request, event_pk):
    """
    The organiser's check-in page.
    Shows all registrations and lets them mark people as checked in.
    Only the event organiser can see this page.
    """
    event = get_object_or_404(Event, pk=event_pk)

    if event.organizer != request.user:
        messages.error(request, "Only the organiser can access the check-in page.")
        return redirect('event_detail', slug=event.slug)

    registrations = Registration.objects.filter(event=event).select_related('user').order_by('user__username')

    # Stats for the header
    total       = registrations.count()
    checked_in  = registrations.filter(checked_in=True).count()
    remaining   = total - checked_in

    return render(request, 'events/checkin_dashboard.html', {
        'event':         event,
        'registrations': registrations,
        'total':         total,
        'checked_in':    checked_in,
        'remaining':     remaining,
    })


@login_required
def checkin_by_code(request, event_pk):
    """
    The organiser types a check-in code (e.g. EVT-A3F9K2)
    and this view finds the registration and marks it as checked in.
    Returns JSON so it works without page reload.
    """
    event = get_object_or_404(Event, pk=event_pk)

    if event.organizer != request.user:
        return JsonResponse({'success': False, 'error': 'Not authorised'}, status=403)

    code = request.POST.get('code', '').strip().upper()

    try:
        reg = Registration.objects.get(check_in_code=code, event=event)

        if reg.checked_in:
            return JsonResponse({
                'success':  False,
                'already':  True,
                'message':  f"{reg.user.username} is already checked in.",
                'name':     reg.user.get_full_name() or reg.user.username,
            })

        reg.checked_in    = True
        reg.checked_in_at = timezone.now()
        reg.save()

        return JsonResponse({
            'success': True,
            'message': f"✅ {reg.user.get_full_name() or reg.user.username} checked in!",
            'name':    reg.user.get_full_name() or reg.user.username,
            'time':    reg.checked_in_at.strftime('%H:%M'),
        })

    except Registration.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error':   f"No registration found for code: {code}",
        })


@login_required
def manual_checkin(request, registration_pk):
    """Organiser manually checks in someone by clicking their name"""
    reg   = get_object_or_404(Registration, pk=registration_pk)
    event = reg.event

    if event.organizer != request.user:
        return JsonResponse({'success': False, 'error': 'Not authorised'})

    reg.checked_in    = True
    reg.checked_in_at = timezone.now()
    reg.save()

    return JsonResponse({
        'success': True,
        'name':    reg.user.get_full_name() or reg.user.username,
    })


# ═══════════════════════════════════════════
#  FEATURE 4 — ADMIN DASHBOARD
# ═══════════════════════════════════════════

@login_required
def admin_dashboard(request):
    """
    Admin-only analytics dashboard.
    Shows charts of registrations, revenue, popular events, categories.
    """
    if not request.user.is_staff:
        messages.error(request, "Admin access only.")
        return redirect('home')

    # ── Key numbers ──
    total_events        = Event.objects.count()
    total_registrations = Registration.objects.count()
    total_users         = Registration.objects.values('user').distinct().count()

    # Total revenue = sum of (event price × number of registrations for that event)
    # We calculate this per event and sum up
    paid_registrations = Registration.objects.select_related('event').filter(event__price__gt=0)
    total_revenue = sum(r.event.price for r in paid_registrations)

    # ── Events by category (for pie/bar chart) ──
    events_by_category = (
        Event.objects
        .values('category__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    category_labels = [e['category__name'] or 'Uncategorised' for e in events_by_category]
    category_counts = [e['count'] for e in events_by_category]

    # ── Registrations per event (top 8 for bar chart) ──
    top_events = (
        Event.objects
        .annotate(reg_count=Count('registrations'))
        .order_by('-reg_count')[:8]
    )
    top_event_labels = [e.title[:25] for e in top_events]
    top_event_counts = [e.reg_count for e in top_events]

    # ── Recent activity (last 10 registrations) ──
    recent_registrations = (
        Registration.objects
        .select_related('user', 'event')
        .order_by('-registered_at')[:10]
    )

    # ── All events for the table ──
    all_events = (
        Event.objects
        .annotate(reg_count=Count('registrations'))
        .select_related('organizer', 'category')
        .order_by('-created_at')
    )

    return render(request, 'events/admin_dashboard.html', {
        # KPIs
        'total_events':        total_events,
        'total_registrations': total_registrations,
        'total_users':         total_users,
        'total_revenue':       total_revenue,

        # Chart data (passed as lists, turned to JSON in template)
        'category_labels': category_labels,
        'category_counts': category_counts,
        'top_event_labels': top_event_labels,
        'top_event_counts': top_event_counts,

        # Tables
        'recent_registrations': recent_registrations,
        'all_events':           all_events,
    })


# new addition
@login_required
def ticket_qr_code(request, registration_pk):
    """Generates a QR code image for a registration"""
    reg = get_object_or_404(Registration, pk=registration_pk, user=request.user)

    # The QR code encodes the check-in code
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(reg.check_in_code)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#FF4D6D", back_color="#0D0D0D")

    # Send it directly as an image response
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return HttpResponse(buffer, content_type='image/png')

def export_attendees(request, event_pk):
    event = get_object_or_404(Event, pk=event_pk)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{event.title}_attendees.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Email', 'Registered At'])

    registrations = Registration.objects.filter(event=event)

    for reg in registrations:
        writer.writerow([
            reg.user.get_full_name() or reg.user.username,
            reg.user.email,
            reg.registered_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response
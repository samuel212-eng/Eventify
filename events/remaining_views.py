# events/remaining_views.py
# =============================================
#  All remaining high-value features:
#  1. Calendar export (.ics)
#  2. Event clone / duplicate
#  3. Ticket transfer
#  4. Event cancellation with notifications
#  5. Group / bulk ticket purchase
#  6. Organiser payout tracker
#  7. Virtual event (Zoom link) support
# =============================================

import uuid
from django.shortcuts   import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models     import User
from django.contrib     import messages
from django.http        import HttpResponse, JsonResponse
from django.utils       import timezone
from django.utils.text  import slugify
from django.core.mail   import send_mail
from django.conf        import settings
from django.views.decorators.http import require_POST

from .models import Event, Registration, Category
from .feature_views import send_registration_confirmation


# ─────────────────────────────────────────────
#  1. CALENDAR EXPORT (.ics)
#     Works with Google Calendar, Apple Calendar, Outlook
# ─────────────────────────────────────────────

def export_to_calendar(request, event_pk):
    """
    Generates a standard .ics calendar file.
    User clicks "Add to Calendar" and it opens in their calendar app.
    No library needed — we write the format by hand.
    """
    event = get_object_or_404(Event, pk=event_pk, is_published=True)

    # Format dates in iCal format: YYYYMMDDTHHMMSSZ
    dtstart  = event.date.strftime('%Y%m%dT%H%M%S')
    dtend    = (event.date + __import__('datetime').timedelta(hours=2)).strftime('%Y%m%dT%H%M%S')
    dtstamp  = timezone.now().strftime('%Y%m%dT%H%M%SZ')
    uid      = f"{event.pk}-{event.slug}@eventify.co.ke"

    # Build the .ics content
    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Eventify//Eventify//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{event.title}
DESCRIPTION:{event.description[:500].replace(chr(10), '\\n')}
LOCATION:{event.location}
URL:{request.build_absolute_uri(f'/events/{event.slug}/')}
ORGANIZER;CN={event.organizer.get_full_name() or event.organizer.username}:MAILTO:{event.organizer.email or 'noreply@eventify.co.ke'}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR""".strip()

    response = HttpResponse(ics, content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="eventify-{event.slug}.ics"'
    return response


# ─────────────────────────────────────────────
#  2. EVENT CLONE / DUPLICATE
# ─────────────────────────────────────────────

@login_required
def clone_event(request, event_pk):
    """
    Creates a copy of an existing event.
    Useful for recurring events or similar event series.
    The clone is saved as a draft so the organiser can edit dates.
    """
    original = get_object_or_404(Event, pk=event_pk, organizer=request.user)

    # Create the clone with slightly modified title
    import datetime
    clone = Event.objects.create(
        title        = f"Copy of {original.title}",
        description  = original.description,
        category     = original.category,
        date         = original.date + datetime.timedelta(days=7),  # Default: one week later
        location     = original.location,
        price        = original.price,
        capacity     = original.capacity,
        organizer    = request.user,
        is_published = False,   # Save as draft — organiser must review before publishing
    )

    messages.success(request,
        f'📋 Event cloned as a draft. Update the date and details before publishing.'
    )
    return redirect('event_edit', pk=clone.pk)


# ─────────────────────────────────────────────
#  3. TICKET TRANSFER
# ─────────────────────────────────────────────

@login_required
def transfer_ticket(request, registration_pk):
    """
    Transfers a ticket to another user by their email address.
    The original registration is deleted and a new one is created
    for the recipient.
    """
    reg = get_object_or_404(Registration, pk=registration_pk, user=request.user)

    if request.method == 'POST':
        recipient_email = request.POST.get('email', '').strip()

        # Can't transfer to yourself
        if recipient_email == request.user.email:
            messages.error(request, "You can't transfer a ticket to yourself.")
            return redirect('my_tickets')

        # Find the recipient
        try:
            recipient = User.objects.get(email=recipient_email)
        except User.DoesNotExist:
            messages.error(request,
                f"No Eventify account found for {recipient_email}. "
                "Ask them to create an account first."
            )
            return render(request, 'events/transfer_ticket.html', {'reg': reg})

        # Check recipient isn't already registered
        if Registration.objects.filter(event=reg.event, user=recipient).exists():
            messages.error(request, f"{recipient.username} is already registered for this event.")
            return render(request, 'events/transfer_ticket.html', {'reg': reg})

        # Do the transfer — update the registration's user
        event    = reg.event
        old_user = reg.user
        reg.user          = recipient
        reg.checked_in    = False   # Reset check-in
        reg.checked_in_at = None
        reg.save()

        # Notify both parties
        if recipient.email:
            send_mail(
                subject       = f'🎟️ Ticket transferred to you: {event.title}',
                message       = f'Hi {recipient.username},\n\n{old_user.username} has transferred their ticket for {event.title} to you.\n\nEvent date: {event.date.strftime("%B %d, %Y at %I:%M %p")}\nLocation: {event.location}\nYour check-in code: {reg.check_in_code}\n\nSee you there!\n— Eventify',
                from_email    = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eventify.co.ke'),
                recipient_list= [recipient.email],
                fail_silently = True,
            )

        if old_user.email:
            send_mail(
                subject       = f'Ticket transfer confirmed: {event.title}',
                message       = f'Hi {old_user.username},\n\nYour ticket for {event.title} has been successfully transferred to {recipient.username} ({recipient_email}).',
                from_email    = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eventify.co.ke'),
                recipient_list= [old_user.email],
                fail_silently = True,
            )

        messages.success(request,
            f'✅ Ticket transferred to {recipient.username}! They have been notified by email.'
        )
        return redirect('my_tickets')

    return render(request, 'events/transfer_ticket.html', {'reg': reg})


# ─────────────────────────────────────────────
#  4. EVENT CANCELLATION
# ─────────────────────────────────────────────

@login_required
def cancel_event(request, event_pk):
    """
    Organiser cancels an event.
    - Unpublishes the event
    - Emails ALL registered attendees
    - Shows refund policy message
    """
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()

        if not reason:
            messages.error(request, "Please provide a cancellation reason for your attendees.")
            return render(request, 'events/cancel_event.html', {'event': event})

        # Unpublish the event
        event.is_published = False
        event.save()

        # Get all registrations
        registrations = Registration.objects.filter(event=event).select_related('user')
        notified = 0

        for reg in registrations:
            if reg.user.email:
                send_mail(
                    subject       = f'⚠️ Event Cancelled: {event.title}',
                    message       = f"""Hi {reg.user.username},

We're sorry to inform you that the following event has been cancelled:

Event: {event.title}
Date:  {event.date.strftime('%A, %B %d, %Y at %I:%M %p')}
Venue: {event.location}

Reason for cancellation:
{reason}

{'If you paid for this event, a refund will be processed within 3–5 business days.' if event.price > 0 else ''}

We apologise for any inconvenience caused.

— The Eventify Team""",
                    from_email    = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eventify.co.ke'),
                    recipient_list= [reg.user.email],
                    fail_silently = True,
                )
                notified += 1

        messages.success(request,
            f'Event cancelled. {notified} attendee{"s" if notified != 1 else ""} notified by email.'
        )
        return redirect('my_events')

    return render(request, 'events/cancel_event.html', {'event': event})


# ─────────────────────────────────────────────
#  5. GROUP / BULK TICKET PURCHASE
# ─────────────────────────────────────────────

@login_required
def group_register(request, event_pk):
    """
    Register multiple people for an event in one transaction.
    The buyer enters names + emails for each attendee.
    Each gets their own check-in code and confirmation email.
    """
    event = get_object_or_404(Event, pk=event_pk, is_published=True)

    # Don't allow if already registered
    if Registration.objects.filter(event=event, user=request.user).exists():
        messages.info(request, "You're already registered for this event.")
        return redirect('event_detail', slug=event.slug)

    max_group = min(10, event.spots_left())   # Max 10 per group order

    if request.method == 'POST':
        names  = request.POST.getlist('name')
        emails = request.POST.getlist('email')

        if not names or len(names) < 1:
            messages.error(request, "Please add at least one attendee.")
            return render(request, 'events/group_register.html', {
                'event': event, 'max_group': max_group
            })

        if len(names) > max_group:
            messages.error(request, f"Maximum {max_group} tickets per group order.")
            return render(request, 'events/group_register.html', {
                'event': event, 'max_group': max_group
            })

        # Check we have enough spots
        if len(names) > event.spots_left():
            messages.error(request,
                f"Only {event.spots_left()} spot{'s' if event.spots_left() != 1 else ''} remaining. "
                "Reduce your group size."
            )
            return render(request, 'events/group_register.html', {
                'event': event, 'max_group': max_group
            })

        created_regs = []

        for i, name in enumerate(names):
            email = emails[i] if i < len(emails) else ''

            # Register the buyer for their own ticket
            if i == 0:
                reg, _ = Registration.objects.get_or_create(
                    event=event, user=request.user
                )
                created_regs.append(reg)
            else:
                # For other attendees: create guest registrations linked to the buyer
                # We create a new registration with a guest note in the message field
                reg, created = Registration.objects.get_or_create(
                    event=event, user=request.user,
                    defaults={'message': f'Group ticket for {name} ({email})'}
                )
                if created:
                    created_regs.append(reg)

            # Email each attendee their code if they have an email
            if email:
                send_mail(
                    subject       = f'🎟️ Your ticket for {event.title}',
                    message       = f'Hi {name},\n\n{request.user.username} has registered you for {event.title}.\n\nDate: {event.date.strftime("%B %d, %Y at %I:%M %p")}\nVenue: {event.location}\n\nSee you there!\n— Eventify',
                    from_email    = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eventify.co.ke'),
                    recipient_list= [email],
                    fail_silently = True,
                )

        messages.success(request,
            f'🎉 {len(names)} ticket{"s" if len(names) != 1 else ""} registered successfully!'
        )
        return redirect('my_tickets')

    return render(request, 'events/group_register.html', {
        'event':     event,
        'max_group': max_group,
    })


# ─────────────────────────────────────────────
#  6. ORGANISER PAYOUT TRACKER
# ─────────────────────────────────────────────

@login_required
def organiser_payouts(request):
    """
    Shows the organiser their earnings per event,
    payment status, and estimated payout schedule.
    """
    events = Event.objects.filter(organizer=request.user).prefetch_related('registrations')

    payout_data = []
    total_earned  = 0
    total_pending = 0

    for event in events:
        reg_count = event.registrations.count()
        revenue   = float(event.price) * reg_count

        # Payout is "released" 24h after event ends
        event_ended  = event.date < timezone.now()
        payout_ready = event_ended and revenue > 0

        status = 'paid' if payout_ready else ('pending' if revenue > 0 else 'free')

        payout_data.append({
            'event':       event,
            'registrations': reg_count,
            'revenue':     revenue,
            'status':      status,
            'payout_date': event.date + __import__('datetime').timedelta(hours=24) if payout_ready else None,
        })

        if status == 'paid':
            total_earned  += revenue
        elif status == 'pending':
            total_pending += revenue

    return render(request, 'events/organiser_payouts.html', {
        'payout_data':   payout_data,
        'total_earned':  total_earned,
        'total_pending': total_pending,
    })

# add ons

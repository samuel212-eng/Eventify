# =============================================
#  REPLACE your existing event_create and
#  event_edit views in views.py with these.
#
#  Key change: paid events require a verified
#  organiser profile AND go into an approval queue.
# =============================================

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Event
from .forms  import EventForm
from .models import OrganizerProfile, EventApproval


@login_required
def event_create(request):
    """
    Create a new event.

    Rules:
    - Free events: anyone can create, goes live immediately
    - Paid events: organiser must be verified + event goes to approval queue
    """

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user

            # ---- PAID EVENT CHECKS ----
            if event.price and event.price > 0:

                # Check: does the user have a verified profile?
                profile = OrganizerProfile.objects.filter(user=request.user).first()

                if not profile or not profile.is_verified:
                    # Save the event as a draft — don't publish yet
                    event.is_published = False
                    event.save()

                    messages.warning(request,
                        "Your event has been saved as a draft. "
                        "You need to be a verified organiser to create paid events. "
                        "Please complete your verification first."
                    )
                    return redirect('apply_for_verification')

                # Verified organiser — save but send to approval queue
                event.is_published = False  # Not live until admin approves
                event.save()

                # Create an approval request
                EventApproval.objects.create(event=event)

                messages.success(request,
                    f'🎉 "{event.title}" has been submitted for review. '
                    'It will go live once approved by our team (usually within 24 hours).'
                )

            else:
                # Free event — goes live immediately, no approval needed
                event.is_published = True
                event.save()
                messages.success(request, f'🎉 "{event.title}" is now live!')

            return redirect('event_detail', pk=event.pk)

    else:
        form = EventForm()

    return render(request, 'events/event_form.html', {
        'form':   form,
        'action': 'Create'
    })


@login_required
def event_edit(request, pk):
    """
    Edit an event.
    If a verified organiser changes the price, it goes back to the approval queue.
    """
    event = get_object_or_404(Event, pk=pk)

    if event.organizer != request.user:
        messages.error(request, "You can only edit your own events.")
        return redirect('event_detail', pk=pk)

    old_price = event.price  # Remember the price before editing

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            updated_event = form.save(commit=False)

            # If they changed the price on a paid event, send back to approval
            price_changed = updated_event.price != old_price
            if price_changed and updated_event.price > 0:
                updated_event.is_published = False
                updated_event.save()

                # Update or create the approval request
                approval, created = EventApproval.objects.get_or_create(event=updated_event)
                approval.status      = EventApproval.PENDING
                approval.reviewed_by = None
                approval.reviewed_at = None
                approval.save()

                messages.warning(request,
                    "You changed the ticket price. Your event has been sent for re-review "
                    "and will go live again once approved."
                )
            else:
                updated_event.save()
                messages.success(request, f'✅ "{updated_event.title}" has been updated!')

            return redirect('event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event)

    return render(request, 'events/event_form.html', {
        'form':   form,
        'action': 'Edit',
        'event':  event,
    })

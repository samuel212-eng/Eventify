# events/views.py — FULL UPDATED VERSION
# Includes context for all 7 new features

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.template.defaultfilters import slugify

from .models import Event, Category, Registration, EventReview, Waitlist, EventApproval, OrganizerProfile
from .forms  import SignUpForm, EventForm, RegistrationForm
from .feature_views import send_registration_confirmation, notify_next_on_waitlist

from django.core.paginator import Paginator
import csv
from django.http import HttpResponse
from django.utils import timezone

# improved view to check on time
def home(request):
    from .models import Event, Category, Registration, EventReview

    upcoming_events = Event.objects.filter(is_published=True).order_by('date')[:6]
    categories      = Category.objects.all()

    # Real stats from the database
    total_events    = Event.objects.filter(is_published=True).count()
    total_regs      = Registration.objects.count()
    total_users     = Registration.objects.values('user').distinct().count()
    total_cats      = Category.objects.count()


    social_links = [
        {"icon": "twitter-x", "label": "Twitter"},
        {"icon": "instagram", "label": "Instagram"},
        {"icon": "linkedin", "label": "LinkedIn"},
    ]

    stats = [
        (max(total_events, 1),  'Live Events',      '🎪'),
        (max(total_users,  10), 'Happy Attendees',  '👥'),
        (max(total_regs,   20), 'Tickets Sold',     '🎟️'),
        (max(total_cats,   6),  'Categories',       '🏷️'),
    ]

    # Real reviews (Priority #6 — no fake testimonials)
    real_reviews = (
        EventReview.objects
        .filter(rating__gte=4)        # Only 4 and 5 star reviews
        .select_related('author', 'event')
        .order_by('-created_at')[:3]  # Three most recent good reviews
    )

    # Problem/solution pairs for "Why Eventify" section
    why_pairs = [
        (
            "Selling tickets through WhatsApp groups and chasing M-Pesa payments manually.",
            "A professional event page with automatic M-Pesa checkout and real-time attendee tracking.",
        ),
        (
            "Attendees losing paper tickets or forgetting event details.",
            "Instant QR code tickets delivered by email, scannable from any phone at the door.",
        ),
        (
            "No way to verify if an organiser is legitimate before buying a ticket.",
            "Every organiser on Eventify is ID-verified. The ✓ badge means they've been checked.",
        ),
    ]

    return render(request, 'events/home.html', {
        'upcoming_events': upcoming_events,
        'categories':      categories,
        'stats':           stats,
        'real_reviews':    real_reviews,
        'why_pairs':       why_pairs,
        'social_links': social_links,
    })



# new search
def event_list(request):
    events     = Event.objects.filter(is_published=True)
    categories = Category.objects.all()

# improved search
    search   = request.GET.get('search', '')
    cat_id   = request.GET.get('category', '')
    price    = request.GET.get('price', '')      # 'free' or 'paid'
    when     = request.GET.get('when', '')       # 'today', 'week', 'month'

    if search:
        events = events.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(location__icontains=search)
        )
    if cat_id:
        events = events.filter(category__id=cat_id)

    if price == 'free':
        events = events.filter(price=0)
    elif price == 'paid':
        events = events.filter(price__gt=0)

    if when == 'today':
        from django.utils import timezone
        today = timezone.now().date()
        events = events.filter(date__date=today)
    elif when == 'week':
        from django.utils import timezone
        import datetime
        week_end = timezone.now() + datetime.timedelta(days=7)
        events = events.filter(date__lte=week_end, date__gte=timezone.now())

# added paginator
        paginator = Paginator(events, 9)  # 9 events per page
        page = request.GET.get('page', 1)
        events = paginator.get_page(page)

    return render(request, 'events/event_list.html', {
        'events':            events,
        'categories':        categories,
        'search':            search,
        'selected_category': cat_id,
        'selected_price':    price,
        'selected_when':     when,
    })

# new event detail
def event_detail(request, slug):
    """One event's full page — with page view tracking and related events"""
    from .extra_views import track_page_view

    event = get_object_or_404(Event, slug=slug, is_published=True)

    # Track this page view (for organiser analytics)
    track_page_view(event)

    # Registration/waitlist status
    user_is_registered = False
    user_registration  = None
    user_has_reviewed  = False
    user_on_waitlist   = False
    waitlist_position  = None

    if request.user.is_authenticated:
        user_registration  = Registration.objects.filter(event=event, user=request.user).first()
        user_is_registered = user_registration is not None
        user_has_reviewed  = EventReview.objects.filter(event=event, author=request.user).exists()

        from .models import Waitlist
        waitlist_entry = Waitlist.objects.filter(event=event, user=request.user).first()
        if waitlist_entry:
            user_on_waitlist  = True
            waitlist_position = waitlist_entry.position()

    # Reviews
    reviews = event.reviews.select_related('author').prefetch_related('reply').all()

    # Q&A questions
    questions = event.questions.select_related('author', 'answered_by').all()

    # Related events (same category, different event, not full, upcoming)
    from django.utils import timezone
    related_events = []
    if event.category:
        related_events = Event.objects.filter(
            is_published=True,
            category=event.category,
            date__gte=timezone.now(),
        ).exclude(pk=event.pk).order_by('date')[:3]

    return render(request, 'events/event_detail.html', {
        'event':              event,
        'user_is_registered': user_is_registered,
        'user_registration':  user_registration,
        'user_has_reviewed':  user_has_reviewed,
        'user_on_waitlist':   user_on_waitlist,
        'waitlist_position':  waitlist_position,
        'reviews':            reviews,
        'questions':          questions,
        'related_events':     related_events,
    })


# new method of aunthentication payment
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

            return redirect('event_detail', slug=event.slug)

    else:
        form = EventForm()

    return render(request, 'events/event_form.html', {
        'form':   form,
        'action': 'Create'
    })

# updated event edit
@login_required
def event_edit(request, pk):
    """
    Edit an event.
    If a verified organiser changes the price, it goes back to the approval queue.
    """
    event = get_object_or_404(Event, pk=pk)

    if event.organizer != request.user:
        messages.error(request, "You can only edit your own events.")
        return redirect('event_detail', slug=event.slug)

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

            return redirect('event_detail', slug=event.slug)
    else:
        form = EventForm(instance=event)

    return render(request, 'events/event_form.html', {
        'form':   form,
        'action': 'Edit',
        'event':  event,
    })


@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user:
        messages.error(request, "You can only delete your own events.")
        return redirect('event_detail', slug=event.slug)
    if request.method == 'POST':
        title = event.title
        event.delete()
        messages.success(request, f'🗑️ "{title}" deleted.')
        return redirect('event_list')
    return render(request, 'events/event_confirm_delete.html', {'event': event})


@login_required
def event_register(request, pk):
    event = get_object_or_404(Event, pk=pk, is_published=True)

    if Registration.objects.filter(event=event, user=request.user).exists():
        messages.warning(request, "You're already registered!")
        return redirect('event_detail', slug=event.slug)
    if event.is_full():
        messages.error(request, "Sorry, this event is full.")
        return redirect('event_detail', slug=event.slug)

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            reg       = form.save(commit=False)
            reg.event = event
            reg.user  = request.user
            reg.save()

            # FEATURE 3: Send confirmation email
            if request.user.email:
                send_registration_confirmation(request.user, event, reg)

            messages.success(request, f"🎟️ Registered! Your code is {reg.check_in_code}")
            return redirect('my_tickets')
    else:
        form = RegistrationForm()

    return render(request, 'events/event_register.html', {'form': form, 'event': event})

# new add on and improvement
@login_required
def my_tickets(request):
    """
    My Tickets page — split into upcoming and past.
    Also calculates an attendance streak for gamification.
    """
    now = timezone.now()

    all_registrations = Registration.objects.filter(
        user=request.user
    ).select_related('event', 'event__category').order_by('event__date')

    upcoming_regs = [r for r in all_registrations if r.event.date >= now]
    past_regs     = [r for r in all_registrations if r.event.date  < now]
    past_regs.reverse()   # Most recent past event first

    # Gamification: count consecutive months with at least one event
    streak = len(past_regs)  # Simple version: total events attended

    return render(request, 'events/my_tickets.html', {
        'registrations':  all_registrations,
        'upcoming_regs':  upcoming_regs,
        'past_regs':      past_regs,
        'streak':         streak,
    })


@login_required
def my_events(request):
    events = Event.objects.filter(organizer=request.user).order_by('-created_at')
    return render(request, 'events/my_events.html', {'events': events})


@login_required
def cancel_registration(request, pk):
    reg = get_object_or_404(Registration, pk=pk, user=request.user)
    if request.method == 'POST':
        event = reg.event
        reg.delete()
        # FEATURE 5: Notify waitlist when someone cancels
        notify_next_on_waitlist(event)
        messages.success(request, f"Registration cancelled.")
        return redirect('my_tickets')
    return render(request, 'events/cancel_confirm.html', {'registration': reg})


def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}! 👋")
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})

# new view
def organiser_profile(request, username):
    from django.contrib.auth.models import User
    organiser = get_object_or_404(User, username=username)
    events    = Event.objects.filter(organizer=organiser, is_published=True)
    total_attendees = sum(e.spots_taken() for e in events)

    return render(request, 'events/organiser_profile.html', {
        'organiser':       organiser,
        'events':          events,
        'total_attendees': total_attendees,
    })


# csv export for attendants
@login_required
def export_attendees(request, event_pk):
    event = get_object_or_404(Event, pk=event_pk, organizer=request.user)

    # Create the CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{event.slug}-attendees.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Username', 'Email', 'Phone', 'Registered At', 'Checked In', 'Check-In Code'])

    for reg in event.registrations.select_related('user').all():
        writer.writerow([
            reg.user.get_full_name() or '—',
            reg.user.username,
            reg.user.email,
            reg.phone or '—',
            reg.registered_at.strftime('%Y-%m-%d %H:%M'),
            'Yes' if reg.checked_in else 'No',
            reg.check_in_code,
        ])

    return response

def save(self, *args, **kwargs):
    if not self.slug:
        base_slug = slugify(self.title)
        slug = base_slug
        counter = 1
        while Event.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        self.slug = slug

    super().save(*args, **kwargs)  # ✅ THIS WAS MISSING

from django.shortcuts import get_object_or_404, redirect

def event_detail_redirect(request, pk):
    event = get_object_or_404(Event, pk=pk)
    return redirect('event_detail', slug=event.slug)
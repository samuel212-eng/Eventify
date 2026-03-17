# events/views.py — FULL UPDATED VERSION
# Includes context for all 7 new features

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from .models import Event, Category, Registration, EventReview, Waitlist
from .forms  import SignUpForm, EventForm, RegistrationForm
from .feature_views import send_registration_confirmation, notify_next_on_waitlist


def home(request):
    upcoming_events = Event.objects.filter(is_published=True).order_by('date')[:6]
    categories      = Category.objects.all()
    total_events    = Event.objects.filter(is_published=True).count()
    return render(request, 'events/home.html', {
        'upcoming_events': upcoming_events,
        'categories':      categories,
        'total_events':    total_events,
    })


def event_list(request):
    events     = Event.objects.filter(is_published=True)
    categories = Category.objects.all()
    search     = request.GET.get('search', '')
    cat_id     = request.GET.get('category', '')

    if search:
        events = events.filter(
            Q(title__icontains=search) | Q(description__icontains=search) | Q(location__icontains=search)
        )
    if cat_id:
        events = events.filter(category__id=cat_id)

    return render(request, 'events/event_list.html', {
        'events':            events,
        'categories':        categories,
        'search':            search,
        'selected_category': cat_id,
    })


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk, is_published=True)

    # Registration status
    user_is_registered = False
    user_registration  = None
    user_has_reviewed  = False
    user_on_waitlist   = False
    waitlist_position  = None

    if request.user.is_authenticated:
        user_registration  = Registration.objects.filter(event=event, user=request.user).first()
        user_is_registered = user_registration is not None
        user_has_reviewed  = EventReview.objects.filter(event=event, author=request.user).exists()

        waitlist_entry = Waitlist.objects.filter(event=event, user=request.user).first()
        if waitlist_entry:
            user_on_waitlist  = True
            waitlist_position = waitlist_entry.position()

    reviews = event.reviews.select_related('author').all()

    return render(request, 'events/event_detail.html', {
        'event':              event,
        'user_is_registered': user_is_registered,
        'user_registration':  user_registration,
        'user_has_reviewed':  user_has_reviewed,
        'user_on_waitlist':   user_on_waitlist,
        'waitlist_position':  waitlist_position,
        'reviews':            reviews,
    })


@login_required
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event           = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, f'🎉 "{event.title}" is now live!')
            return redirect('event_detail', pk=event.pk)
    else:
        form = EventForm()
    return render(request, 'events/event_form.html', {'form': form, 'action': 'Create'})


@login_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user:
        messages.error(request, "You can only edit your own events.")
        return redirect('event_detail', pk=pk)
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ "{event.title}" updated!')
            return redirect('event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event)
    return render(request, 'events/event_form.html', {'form': form, 'action': 'Edit', 'event': event})


@login_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user:
        messages.error(request, "You can only delete your own events.")
        return redirect('event_detail', pk=pk)
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
        return redirect('event_detail', pk=pk)
    if event.is_full():
        messages.error(request, "Sorry, this event is full.")
        return redirect('event_detail', pk=pk)

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


@login_required
def my_tickets(request):
    registrations = Registration.objects.filter(user=request.user).order_by('-registered_at')
    return render(request, 'events/my_tickets.html', {'registrations': registrations})


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

# events/models.py — THE ONE TRUE MODELS FILE
# All models live here. No other file defines models.

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
import random, string
from django.utils.text import slugify


def generate_checkin_code():
    """Creates a short unique code like EVT-A3F9K2"""
    chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"EVT-{chars}"


# ──────────────────────────────────────────────
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


# ──────────────────────────────────────────────
class Event(models.Model):
    title        = models.CharField(max_length=200)
    description  = models.TextField()
    category     = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    date         = models.DateTimeField()
    location     = models.CharField(max_length=300)
    image        = models.ImageField(upload_to='events/', blank=True, null=True)
    price        = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    capacity     = models.PositiveIntegerField(default=100)
    organizer    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_events')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)

# added slug field
    slug = models.SlugField(max_length=250, unique=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-generate the slug from the title when saving
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            # If slug already exists, add a number: nairobi-tech-summit-2
            while Event.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def spots_taken(self):
        return self.registrations.count()

    def spots_left(self):
        return max(0, self.capacity - self.spots_taken())

    def is_full(self):
        return self.spots_left() <= 0

    def capacity_percentage(self):
        if self.capacity == 0:
            return 100
        return min(int((self.spots_taken() / self.capacity) * 100), 100)

    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / reviews.count(), 1)

    def review_count(self):
        return self.reviews.count()

    class Meta:
        ordering = ['date']

    virtual_link = models.URLField(
        blank=True,
        help_text="Zoom/Google Meet/YouTube Live link for online events"
    )
    is_virtual = models.BooleanField(default=False)


# ──────────────────────────────────────────────
class Registration(models.Model):
    event         = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    phone         = models.CharField(max_length=20, blank=True)
    message       = models.TextField(blank=True)
    checked_in    = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    check_in_code = models.CharField(max_length=12, unique=True, blank=True, default=generate_checkin_code)

    def __str__(self):
        return f"{self.user.username} → {self.event.title}"

    class Meta:
        unique_together = ('event', 'user')


# ──────────────────────────────────────────────
class EventReview(models.Model):
    event      = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews')
    author     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_reviews')
    rating     = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment    = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username} → {self.event.title} ({self.rating}★)"

    class Meta:
        unique_together = ('event', 'author')
        ordering        = ['-created_at']


# ──────────────────────────────────────────────
class Waitlist(models.Model):
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='waitlist')
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_waitlists')
    joined_at   = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)

    def position(self):
        return Waitlist.objects.filter(event=self.event, joined_at__lte=self.joined_at).count()

    def __str__(self):
        return f"{self.user.username} waiting for {self.event.title}"

    class Meta:
        unique_together = ('event', 'user')
        ordering        = ['joined_at']


# ──────────────────────────────────────────────
class MpesaPayment(models.Model):
    PENDING   = 'pending'
    COMPLETED = 'completed'
    FAILED    = 'failed'
    STATUS_CHOICES = [
        (PENDING,   'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED,    'Failed'),
    ]
    registration         = models.OneToOneField(Registration, on_delete=models.CASCADE, related_name='payment')
    phone_number         = models.CharField(max_length=15)
    amount               = models.DecimalField(max_digits=10, decimal_places=2)
    checkout_request_id  = models.CharField(max_length=200, blank=True)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)
    status               = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    result_description   = models.TextField(blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} | {self.amount} KES | {self.status}"


# ──────────────────────────────────────────────
class OrganizerProfile(models.Model):
    UNVERIFIED = 'unverified'
    PENDING    = 'pending'
    APPROVED   = 'approved'
    REJECTED   = 'rejected'
    SUSPENDED  = 'suspended'
    STATUS_CHOICES = [
        (UNVERIFIED, 'Unverified'),
        (PENDING,    'Pending Review'),
        (APPROVED,   'Approved ✓'),
        (REJECTED,   'Rejected'),
        (SUSPENDED,  'Suspended'),
    ]
    user              = models.OneToOneField(User, on_delete=models.CASCADE, related_name='organizer_profile')
    phone_number      = models.CharField(max_length=20)
    id_number         = models.CharField(max_length=20)
    id_document       = models.ImageField(upload_to='verification/ids/', blank=True, null=True)
    selfie_with_id    = models.ImageField(upload_to='verification/selfies/', blank=True, null=True)
    organization_name = models.CharField(max_length=200, blank=True)
    website           = models.URLField(blank=True)
    bio               = models.TextField(max_length=500, blank=True)
    social_media      = models.CharField(max_length=200, blank=True)
    mpesa_number      = models.CharField(max_length=15, blank=True)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default=UNVERIFIED)
    rejection_reason  = models.TextField(blank=True)
    reviewed_by       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_profiles')
    reviewed_at       = models.DateTimeField(null=True, blank=True)
    submitted_at      = models.DateTimeField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.status}"

    @property
    def is_verified(self):
        return self.status == self.APPROVED

    @property
    def can_create_paid_events(self):
        return self.status == self.APPROVED


# ──────────────────────────────────────────────
class EventApproval(models.Model):
    PENDING  = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (PENDING,  'Pending Review'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]
    event            = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='approval')
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    rejection_reason = models.TextField(blank=True)
    reviewed_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_events')
    reviewed_at      = models.DateTimeField(null=True, blank=True)
    submitted_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event.title} — {self.status}"


# ──────────────────────────────────────────────
class EventReport(models.Model):
    SCAM          = 'scam'
    FAKE_EVENT    = 'fake_event'
    WRONG_INFO    = 'wrong_info'
    INAPPROPRIATE = 'inappropriate'
    OTHER         = 'other'
    REASON_CHOICES = [
        (SCAM,          'This looks like a scam'),
        (FAKE_EVENT,    'This event does not exist'),
        (WRONG_INFO,    'Wrong or misleading information'),
        (INAPPROPRIATE, 'Inappropriate content'),
        (OTHER,         'Other'),
    ]
    event       = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_reports')
    reason      = models.CharField(max_length=30, choices=REASON_CHOICES)
    details     = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Report: {self.event.title} by {self.reported_by.username}"

    class Meta:
        unique_together = ('event', 'reported_by')



# new add on classes
class OrganizerFollow(models.Model):
    """
    A user follows an organiser.
    When that organiser creates a new event,
    followers get an email notification.
    """
    follower   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    organizer  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.follower.username} follows {self.organizer.username}"

    class Meta:
        unique_together = ('follower', 'organizer')
        ordering        = ['-created_at']


class SavedEvent(models.Model):
    """
    A user saves (bookmarks) an event they are interested in.
    They can view all saved events from their dashboard.
    """
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_events')
    event    = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} saved {self.event.title}"

    class Meta:
        unique_together = ('user', 'event')
        ordering        = ['-saved_at']




class PromoCode(models.Model):
    """
    Organisers create discount codes for their events.
    E.g. EARLYBIRD50 = 50% off, max 20 uses, expires April 30
    """
    event           = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='promo_codes')
    code            = models.CharField(max_length=20, unique=True)
    discount_type   = models.CharField(max_length=10, choices=[('percent','Percentage'),('fixed','Fixed Amount')], default='percent')
    discount_value  = models.DecimalField(max_digits=6, decimal_places=2, help_text="50 = 50% off or KES 50 off")
    max_uses        = models.PositiveIntegerField(default=100)
    times_used      = models.PositiveIntegerField(default=0)
    expires_at      = models.DateTimeField(null=True, blank=True)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} — {self.discount_value}{'%' if self.discount_type=='percent' else ' KES'} off {self.event.title}"

    def is_valid(self):
        from django.utils import timezone
        if not self.is_active:
            return False, "This promo code is no longer active."
        if self.times_used >= self.max_uses:
            return False, "This promo code has reached its usage limit."
        if self.expires_at and timezone.now() > self.expires_at:
            return False, "This promo code has expired."
        return True, "Valid"

    def calculate_discount(self, original_price):
        """Returns the discounted price"""
        if self.discount_type == 'percent':
            discount = original_price * (self.discount_value / 100)
        else:
            discount = self.discount_value
        return max(0, original_price - discount)


# ─────────────────────────────────────────────
#  IN-APP NOTIFICATIONS
# ─────────────────────────────────────────────

class Notification(models.Model):
    """
    In-app notifications shown in the navbar bell icon.
    Created automatically by signals/views when things happen.
    """
    TYPE_CHOICES = [
        ('event_approved',   '✅ Event Approved'),
        ('event_rejected',   '❌ Event Rejected'),
        ('new_registration', '🎟️ New Registration'),
        ('waitlist_spot',    '🎉 Waitlist Spot Available'),
        ('new_review',       '⭐ New Review'),
        ('new_follower',     '👤 New Follower'),
        ('event_reminder',   '⏰ Event Reminder'),
        ('new_event',        '🎪 New Event from Following'),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notif_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    link       = models.CharField(max_length=300, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} — {self.title}"

    class Meta:
        ordering = ['-created_at']


# ─────────────────────────────────────────────
#  EVENT Q&A
# ─────────────────────────────────────────────

class EventQuestion(models.Model):
    """
    Users ask questions about an event before registering.
    The organiser can answer publicly.
    """
    event      = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='questions')
    author     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='asked_questions')
    question   = models.TextField(max_length=500)
    answer     = models.TextField(blank=True, help_text="Organiser's answer")
    answered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='answered_questions')
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Q: {self.question[:50]} on {self.event.title}"

    class Meta:
        ordering = ['-created_at']


# ─────────────────────────────────────────────
#  PAGE VIEW TRACKER (for organiser analytics)
# ─────────────────────────────────────────────

class EventPageView(models.Model):
    """
    Tracks how many times each event page has been visited.
    Stored as a simple daily count to avoid bloating the DB.
    """
    event      = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='page_views')
    date       = models.DateField(auto_now_add=True)
    view_count = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.event.title} — {self.date} ({self.view_count} views)"

    class Meta:
        unique_together = ('event', 'date')


# ─────────────────────────────────────────────
#  EVENT GALLERY
# ─────────────────────────────────────────────

class EventGalleryImage(models.Model):
    """Multiple photos per event"""
    event      = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='gallery')
    image      = models.ImageField(upload_to='events/gallery/')
    caption    = models.CharField(max_length=200, blank=True)
    order      = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.event.title}"

    class Meta:
        ordering = ['order', 'created_at']


# ─────────────────────────────────────────────
#  REVIEW REPLY
# ─────────────────────────────────────────────

class ReviewReply(models.Model):
    """Organiser replies to a review publicly"""
    review     = models.OneToOneField('EventReview', on_delete=models.CASCADE, related_name='reply')
    author     = models.ForeignKey(User, on_delete=models.CASCADE)
    message    = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply to review by {self.review.author.username}"


# new models
# ── MULTI-IMAGE GALLERY ──────────────────────
class EventGalleryImage(models.Model):
    """Multiple photos per event — swipeable gallery"""
    event   = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='gallery')
    image   = models.ImageField(upload_to='events/gallery/')
    caption = models.CharField(max_length=200, blank=True)
    order   = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Gallery image for {self.event.title}"


# ── RECURRING EVENTS ─────────────────────────
class RecurringEvent(models.Model):
    """
    Links multiple Event objects together as a recurring series.
    e.g. 'Weekly Django Meetup' creates one Event per week.
    """
    DAILY   = 'daily'
    WEEKLY  = 'weekly'
    MONTHLY = 'monthly'
    FREQ_CHOICES = [
        (DAILY,   'Daily'),
        (WEEKLY,  'Weekly'),
        (MONTHLY, 'Monthly'),
    ]

    # The original (parent) event
    parent_event = models.ForeignKey(
        'Event', on_delete=models.CASCADE, related_name='recurrence_parent'
    )
    frequency    = models.CharField(max_length=10, choices=FREQ_CHOICES)
    repeat_count = models.PositiveIntegerField(
        default=4, help_text="How many future occurrences to create"
    )
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parent_event.title} — {self.frequency}"


# ── CAPACITY TIERS (e.g. General, VIP, VVIP) ─
class TicketTier(models.Model):
    """
    Multiple ticket types per event with different prices and capacities.
    e.g. General KES 500 (200 tickets), VIP KES 2000 (50 tickets)
    """
    event    = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='tiers')
    name     = models.CharField(max_length=100, help_text='e.g. General, VIP, VVIP, Early Bird')
    price    = models.DecimalField(max_digits=8, decimal_places=2)
    capacity = models.PositiveIntegerField()
    perks    = models.TextField(blank=True, help_text='Comma-separated perks, e.g. Free drink, Front row, Backstage access')
    is_active = models.BooleanField(default=True)
    order    = models.PositiveIntegerField(default=0)

    def spots_taken(self):
        return TierRegistration.objects.filter(tier=self).count()

    def spots_left(self):
        return max(0, self.capacity - self.spots_taken())

    def is_sold_out(self):
        return self.spots_left() <= 0

    def perks_list(self):
        return [p.strip() for p in self.perks.split(',') if p.strip()]

    class Meta:
        ordering = ['order', 'price']

    def __str__(self):
        return f"{self.name} — KES {self.price} ({self.event.title})"


class TierRegistration(models.Model):
    """Tracks which ticket tier a user registered for"""
    registration = models.OneToOneField(
        'Registration', on_delete=models.CASCADE, related_name='tier_reg'
    )
    tier = models.ForeignKey(TicketTier, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.registration.user.username} — {self.tier.name}"


# ── GAMIFICATION / POINTS ────────────────────
class AttendeePoints(models.Model):
    """Points system — earned by registering, attending, reviewing"""
    user   = models.OneToOneField(User, on_delete=models.CASCADE, related_name='points')
    total  = models.PositiveIntegerField(default=0)
    level  = models.CharField(max_length=20, default='Newcomer')

    LEVELS = [
        (0,   'Newcomer'),
        (50,  'Explorer'),
        (150, 'Regular'),
        (300, 'Enthusiast'),
        (500, 'VIP'),
        (1000,'Legend'),
    ]

    def recalculate_level(self):
        for threshold, label in reversed(self.LEVELS):
            if self.total >= threshold:
                self.level = label
                break

    def __str__(self):
        return f"{self.user.username}: {self.total} pts ({self.level})"


class PointTransaction(models.Model):
    """Every time a user earns points"""
    ACTIONS = [
        ('register',  '🎟️ Registered for event',   10),
        ('attend',    '✅ Attended event',          25),
        ('review',    '⭐ Left a review',           15),
        ('early_bird','⚡ Early bird registration', 20),
        ('follow',    '👤 Followed an organiser',    5),
        ('share',     '📢 Shared an event',          5),
    ]
    ACTION_CHOICES = [(a[0], a[1]) for a in ACTIONS]
    POINTS_MAP     = {a[0]: a[2] for a in ACTIONS}

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_txns')
    action     = models.CharField(max_length=20, choices=ACTION_CHOICES)
    points     = models.PositiveIntegerField()
    event      = models.ForeignKey('Event', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} +{self.points} ({self.action})"

    class Meta:
        ordering = ['-created_at']


# ── SPEAKER CARDS ─────────────────────────────
class EventSpeaker(models.Model):
    """Speakers or performers at an event"""
    event   = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='speakers')
    name    = models.CharField(max_length=200)
    title   = models.CharField(max_length=200, blank=True, help_text='e.g. CEO at Safaricom, Lead Engineer')
    bio     = models.TextField(max_length=500, blank=True)
    photo   = models.ImageField(upload_to='speakers/', blank=True, null=True)
    twitter = models.CharField(max_length=100, blank=True)
    linkedin= models.URLField(blank=True)
    order   = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} at {self.event.title}"


# ── SPONSORS ──────────────────────────────────
class EventSponsor(models.Model):
    """Sponsors with tier-based display"""
    PLATINUM = 'platinum'
    GOLD     = 'gold'
    SILVER   = 'silver'
    BRONZE   = 'bronze'
    TIER_CHOICES = [
        (PLATINUM, 'Platinum'),
        (GOLD,     'Gold'),
        (SILVER,   'Silver'),
        (BRONZE,   'Bronze'),
    ]

    event   = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='sponsors')
    name    = models.CharField(max_length=200)
    logo    = models.ImageField(upload_to='sponsors/', blank=True, null=True)
    website = models.URLField(blank=True)
    tier    = models.CharField(max_length=10, choices=TIER_CHOICES, default=SILVER)
    order   = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.tier}) — {self.event.title}"


# ── FAQ ───────────────────────────────────────
class EventFAQ(models.Model):
    """Frequently asked questions for an event"""
    event    = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=300)
    answer   = models.TextField()
    order    = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"FAQ: {self.question[:50]}"

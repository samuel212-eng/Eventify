# events/management/commands/send_weekly_digest.py
# =============================================
#  Sends a "What's On This Week" email to all
#  registered users every Monday morning.
#
#  Run:  python manage.py send_weekly_digest
#  Schedule: every Monday at 8am with Task Scheduler
# =============================================

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import datetime

from events.models import Event, Registration


class Command(BaseCommand):
    help = 'Sends weekly event digest to all users'

    def handle(self, *args, **kwargs):
        now      = timezone.now()
        week_end = now + datetime.timedelta(days=7)

        # Get events happening this week
        this_week = Event.objects.filter(
            is_published=True,
            date__gte=now,
            date__lte=week_end,
        ).order_by('date')[:5]

        if not this_week:
            self.stdout.write("No events this week — skipping digest.")
            return

        # Build the email body
        event_lines = ""
        for event in this_week:
            price = "Free" if event.price == 0 else f"KES {event.price}"
            event_lines += f"""
📅 {event.title}
   {event.date.strftime('%A, %B %d · %I:%M %p')}
   📍 {event.location}
   💰 {price} · {event.spots_left()} spots left
   http://127.0.0.1:8000/events/{event.slug}/

"""

        # Send to all users with emails
        users = User.objects.filter(email__isnull=False).exclude(email='')
        sent  = 0

        for user in users:
            subject = f"🔥 What's happening this week on Eventify"
            message = f"""
Hi {user.first_name or user.username},

Here are the top events happening this week:

{event_lines}
Browse all events: http://127.0.0.1:8000/events/

Have a great week,
The Eventify Team

---
To unsubscribe, reply with "unsubscribe" in the subject line.
            """.strip()

            try:
                send_mail(
                    subject        = subject,
                    message        = message,
                    from_email     = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eventify.co.ke'),
                    recipient_list = [user.email],
                    fail_silently  = True,
                )
                sent += 1
                self.stdout.write(f"  ✓ Digest sent to {user.email}")
            except Exception as e:
                self.stdout.write(f"  ✗ Failed: {user.email} — {e}")

        self.stdout.write(self.style.SUCCESS(f"\nDone. Sent digest to {sent} users."))

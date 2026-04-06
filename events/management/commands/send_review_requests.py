# events/management/commands/send_review_requests.py
# =============================================
#  Management command: sends review request emails
#  24 hours after an event ends.
#
#  Run manually:  python manage.py send_review_requests
#  Schedule with: Windows Task Scheduler or cron job
#  Cron example:  0 * * * * python manage.py send_review_requests
# =============================================

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
import datetime

from events.models import Event, Registration, EventReview


class Command(BaseCommand):
    help = 'Sends review request emails to attendees 24 hours after their event ends'

    def handle(self, *args, **kwargs):

        # Find events that ended between 24 and 48 hours ago
        now      = timezone.now()
        from_dt  = now - datetime.timedelta(hours=48)
        to_dt    = now - datetime.timedelta(hours=24)

        past_events = Event.objects.filter(
            date__gte=from_dt,
            date__lte=to_dt,
            is_published=True,
        )

        total_sent = 0

        for event in past_events:
            # Get registrations for this event
            registrations = Registration.objects.filter(
                event=event
            ).select_related('user')

            for reg in registrations:
                user = reg.user

                # Skip if they've already reviewed this event
                if EventReview.objects.filter(event=event, author=user).exists():
                    continue

                # Skip if no email address
                if not user.email:
                    continue

                subject = f"How was {event.title}? 🎉 Leave a quick review"

                message = f"""
Hi {user.first_name or user.username},

You attended {event.title} — we hope it was amazing!

Quick favour: could you leave a short review? It takes 30 seconds and helps other attendees decide whether to go.

Leave your review here:
{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/events/{event.slug}/

Your feedback helps organisers improve and helps the community discover great events.

Thanks,
The Eventify Team
                """.strip()

                try:
                    send_mail(
                        subject        = subject,
                        message        = message,
                        from_email     = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@eventify.co.ke'),
                        recipient_list = [user.email],
                        fail_silently  = True,
                    )
                    total_sent += 1
                    self.stdout.write(f"  ✓ Review request sent to {user.email} for '{event.title}'")
                except Exception as e:
                    self.stdout.write(f"  ✗ Failed for {user.email}: {e}")

        self.stdout.write(
            self.style.SUCCESS(f"\nDone. Sent {total_sent} review request email(s).")
        )

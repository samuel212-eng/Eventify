# events/verification_views.py
# =============================================
#  Views for organiser verification flow
# =============================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import Event, Registration
from .models import OrganizerProfile, EventApproval, EventReport
from .verification_forms import OrganizerVerificationForm, EventReportForm


# ---- Helper: is this user an admin? ----
def is_admin(user):
    return user.is_staff


# --------------------------------------------------
# APPLY FOR ORGANISER VERIFICATION
# --------------------------------------------------
@login_required
def apply_for_verification(request):
    """
    The form where a user submits their ID and details
    to become a verified organiser.
    """

    # If they already have a profile, show its status instead
    profile = OrganizerProfile.objects.filter(user=request.user).first()

    if profile:
        if profile.status == OrganizerProfile.APPROVED:
            messages.success(request, "You are already a verified organiser!")
            return redirect('my_events')

        if profile.status == OrganizerProfile.PENDING:
            return render(request, 'events/verification_pending.html', {'profile': profile})

    if request.method == 'POST':
        form = OrganizerVerificationForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user         = request.user
            profile.status       = OrganizerProfile.PENDING
            profile.submitted_at = timezone.now()
            profile.save()

            # Email the admin to review
            _notify_admin_new_application(request.user)

            messages.success(request,
                "✅ Application submitted! We'll review your details within 24–48 hours."
            )
            return redirect('verification_pending')
    else:
        form = OrganizerVerificationForm(instance=profile)

    return render(request, 'events/apply_verification.html', {'form': form})


@login_required
def verification_pending(request):
    """Shows the 'your application is under review' page"""
    profile = get_object_or_404(OrganizerProfile, user=request.user)
    return render(request, 'events/verification_pending.html', {'profile': profile})


# --------------------------------------------------
# REPORT AN EVENT
# --------------------------------------------------
@login_required
def report_event(request, event_pk):
    """Any user can flag a suspicious event"""
    event = get_object_or_404(Event, pk=event_pk)

    # Can't report your own event
    if event.organizer == request.user:
        messages.error(request, "You cannot report your own event.")
        return redirect('event_detail', pk=event_pk)

    # Already reported?
    if EventReport.objects.filter(event=event, reported_by=request.user).exists():
        messages.warning(request, "You've already reported this event. We're reviewing it.")
        return redirect('event_detail', pk=event_pk)

    if request.method == 'POST':
        form = EventReportForm(request.POST)
        if form.is_valid():
            report             = form.save(commit=False)
            report.event       = event
            report.reported_by = request.user
            report.save()

            # If an event gets 3+ reports, automatically unpublish it
            # and notify admin immediately
            report_count = EventReport.objects.filter(event=event, is_resolved=False).count()
            if report_count >= 3:
                event.is_published = False
                event.save()
                _notify_admin_flagged_event(event, report_count)

            messages.success(request,
                "Thank you for reporting this. Our team will investigate within 24 hours."
            )
            return redirect('event_detail', pk=event_pk)
    else:
        form = EventReportForm()

    return render(request, 'events/report_event.html', {'form': form, 'event': event})


# --------------------------------------------------
# ADMIN: Review verification applications
# --------------------------------------------------
@user_passes_test(is_admin)
def admin_verification_queue(request):
    """
    Admin page showing all pending organiser applications.
    Only staff users can see this.
    """
    pending   = OrganizerProfile.objects.filter(status=OrganizerProfile.PENDING).order_by('submitted_at')
    approved  = OrganizerProfile.objects.filter(status=OrganizerProfile.APPROVED).order_by('-reviewed_at')[:20]
    rejected  = OrganizerProfile.objects.filter(status=OrganizerProfile.REJECTED).order_by('-reviewed_at')[:10]
    suspended = OrganizerProfile.objects.filter(status=OrganizerProfile.SUSPENDED)

    return render(request, 'events/admin_verification_queue.html', {
        'pending':   pending,
        'approved':  approved,
        'rejected':  rejected,
        'suspended': suspended,
    })


@user_passes_test(is_admin)
def admin_review_organiser(request, profile_id):
    """Admin approves or rejects an organiser application"""
    profile = get_object_or_404(OrganizerProfile, pk=profile_id)

    if request.method == 'POST':
        action = request.POST.get('action')   # 'approve', 'reject', or 'suspend'
        reason = request.POST.get('reason', '')

        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()

        if action == 'approve':
            profile.status = OrganizerProfile.APPROVED
            _notify_organiser_approved(profile.user)
            messages.success(request, f"{profile.user.username} has been approved as a verified organiser.")

        elif action == 'reject':
            if not reason:
                messages.error(request, "Please provide a rejection reason.")
                return redirect('admin_review_organiser', profile_id=profile_id)
            profile.status           = OrganizerProfile.REJECTED
            profile.rejection_reason = reason
            _notify_organiser_rejected(profile.user, reason)
            messages.warning(request, f"{profile.user.username}'s application has been rejected.")

        elif action == 'suspend':
            profile.status           = OrganizerProfile.SUSPENDED
            profile.rejection_reason = reason
            # Also unpublish all their events
            Event.objects.filter(organizer=profile.user).update(is_published=False)
            messages.error(request, f"{profile.user.username} has been suspended. All their events are unpublished.")

        profile.save()
        return redirect('admin_verification_queue')

    return render(request, 'events/admin_review_organiser.html', {'profile': profile})


# --------------------------------------------------
# ADMIN: Review event approvals
# --------------------------------------------------
@user_passes_test(is_admin)
def admin_event_approval_queue(request):
    """Shows paid events waiting for approval"""
    pending_events = EventApproval.objects.filter(
        status=EventApproval.PENDING
    ).select_related('event', 'event__organizer').order_by('submitted_at')

    reports = EventReport.objects.filter(
        is_resolved=False
    ).select_related('event', 'reported_by').order_by('-created_at')

    return render(request, 'events/admin_event_queue.html', {
        'pending_events': pending_events,
        'reports':        reports,
    })


@user_passes_test(is_admin)
def admin_review_event(request, approval_id):
    """Admin approves or rejects a paid event"""
    approval = get_object_or_404(EventApproval, pk=approval_id)
    event    = approval.event

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '')

        approval.reviewed_by = request.user
        approval.reviewed_at = timezone.now()

        if action == 'approve':
            approval.status    = EventApproval.APPROVED
            event.is_published = True
            event.save()
            _notify_organiser_event_approved(event)
            messages.success(request, f'"{event.title}" is now live.')

        elif action == 'reject':
            approval.status          = EventApproval.REJECTED
            approval.rejection_reason = reason
            event.is_published       = False
            event.save()
            _notify_organiser_event_rejected(event, reason)
            messages.warning(request, f'"{event.title}" has been rejected.')

        approval.save()
        return redirect('admin_event_approval_queue')

    return render(request, 'events/admin_review_event.html', {
        'approval': approval,
        'event':    event,
    })


# --------------------------------------------------
# EMAIL NOTIFICATION HELPERS
# (Replace print() with real send_mail() once SMTP is configured)
# --------------------------------------------------

def _notify_admin_new_application(user):
    print(f"[EMAIL] New organiser application from {user.username}")
    # send_mail(
    #     subject='New Organiser Verification Application',
    #     message=f'{user.username} ({user.email}) has applied to become a verified organiser.',
    #     from_email=settings.DEFAULT_FROM_EMAIL,
    #     recipient_list=[settings.ADMIN_EMAIL],
    # )

def _notify_admin_flagged_event(event, report_count):
    print(f"[EMAIL] Event '{event.title}' auto-unpublished after {report_count} reports")

def _notify_organiser_approved(user):
    print(f"[EMAIL] Notifying {user.email} — application approved")

def _notify_organiser_rejected(user, reason):
    print(f"[EMAIL] Notifying {user.email} — rejected: {reason}")

def _notify_organiser_event_approved(event):
    print(f"[EMAIL] Notifying {event.organizer.email} — event '{event.title}' approved")

def _notify_organiser_event_rejected(event, reason):
    print(f"[EMAIL] Notifying {event.organizer.email} — event '{event.title}' rejected: {reason}")

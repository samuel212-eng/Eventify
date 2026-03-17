from django.contrib import admin
from .models import (
    Event, Category, Registration,
    EventReview, Waitlist, MpesaPayment,
    OrganizerProfile, EventApproval, EventReport
)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display  = ['title', 'organizer', 'date', 'capacity', 'is_published']
    list_filter   = ['is_published', 'category']
    search_fields = ['title']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'event', 'registered_at', 'checked_in', 'check_in_code']
    list_filter   = ['checked_in']

@admin.register(EventReview)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['author', 'event', 'rating', 'created_at']

@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'joined_at', 'notified_at']

@admin.register(MpesaPayment)
class MpesaPaymentAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'amount', 'status', 'mpesa_receipt_number', 'created_at']
    list_filter  = ['status']

@admin.register(OrganizerProfile)
class OrganizerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'submitted_at', 'reviewed_at']
    list_filter  = ['status']

@admin.register(EventApproval)
class EventApprovalAdmin(admin.ModelAdmin):
    list_display = ['event', 'status', 'submitted_at']
    list_filter  = ['status']

@admin.register(EventReport)
class EventReportAdmin(admin.ModelAdmin):
    list_display = ['event', 'reported_by', 'reason', 'is_resolved']
    list_filter  = ['is_resolved', 'reason']

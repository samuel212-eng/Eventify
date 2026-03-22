from django.urls import path
from . import views, feature_views, verification_views, mpesa_views

urlpatterns = [
    path('',                             views.home,               name='home'),
    path('events/',                      views.event_list,         name='event_list'),
    path('events/<int:pk>/',             views.event_detail,       name='event_detail'),
    path('events/create/',               views.event_create,       name='event_create'),
    path('events/<int:pk>/edit/',        views.event_edit,         name='event_edit'),
    path('events/<int:pk>/delete/',      views.event_delete,       name='event_delete'),
    path('events/<int:pk>/register/',    views.event_register,     name='event_register'),
    path('cancel/<int:pk>/',             views.cancel_registration, name='cancel_registration'),
    path('my-tickets/',                  views.my_tickets,         name='my_tickets'),
    path('my-events/',                   views.my_events,          name='my_events'),
    path('signup/',                      views.signup,             name='signup'),

    # ── Feature 1: Reviews
    path('events/<int:event_pk>/review/',       feature_views.submit_review, name='submit_review'),
    path('reviews/<int:review_pk>/delete/',     feature_views.delete_review, name='delete_review'),

    # ── Feature 4: Admin dashboad
    path('dashboard/',                          feature_views.admin_dashboard, name='admin_dashboard'),

    # ── Feature 5: Waitlist
    path('events/<int:event_pk>/waitlist/join/', feature_views.join_waitlist,  name='join_waitlist'),
    path('events/<int:event_pk>/waitlist/leave/',feature_views.leave_waitlist, name='leave_waitlist'),

    # ── Feature 6: Check-in
    path('events/<int:event_pk>/checkin/',        feature_views.checkin_dashboard, name='checkin_dashboard'),
    path('events/<int:event_pk>/checkin/code/',   feature_views.checkin_by_code,   name='checkin_by_code'),
    path('checkin/manual/<int:registration_pk>/', feature_views.manual_checkin,    name='manual_checkin'),

    # ── M-Pesa payments
    path('events/<int:event_pk>/pay/',        mpesa_views.payment_page,         name='payment_page'),
    path('events/<int:event_pk>/pay/start/',  mpesa_views.initiate_payment,     name='initiate_payment'),
    path('payment/waiting/<int:payment_id>/', mpesa_views.payment_waiting,      name='payment_waiting'),
    path('payment/status/<int:payment_id>/',  mpesa_views.check_payment_status, name='check_payment_status'),
    path('mpesa/callback/',                   mpesa_views.mpesa_callback,       name='mpesa_callback'),

    # ── Verification
    path('verify/',                               verification_views.apply_for_verification,    name='apply_for_verification'),
    path('verify/pending/',                       verification_views.verification_pending,       name='verification_pending'),
    path('events/<int:event_pk>/report/',         verification_views.report_event,              name='report_event'),
    path('admin-panel/verifications/',            verification_views.admin_verification_queue,  name='admin_verification_queue'),
    path('admin-panel/verify/<int:profile_id>/',  verification_views.admin_review_organiser,    name='admin_review_organiser'),
    path('admin-panel/events/',                   verification_views.admin_event_approval_queue,name='admin_event_approval_queue'),
    path('admin-panel/events/<int:approval_id>/', verification_views.admin_review_event,        name='admin_review_event'),
]

from django.urls import path
from . import views, feature_views, verification_views, mpesa_views
from . import paypal_views
from . import next10_views
from . import extra_views, pdf_views


urlpatterns = [
    path('',                             views.home,               name='home'),
    path('events/',                      views.event_list,         name='event_list'),

    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/', views.event_detail_redirect, name='event_detail_redirect'),
    path('events/<slug:slug>/', views.event_detail, name='event_detail'),


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
   # new urls
    path('tickets/<int:registration_pk>/qr/', feature_views.ticket_qr_code, name='ticket_qr'),
    # path('organiser/<str:username>/', views.organiser_profile, name='organiser_profile'),
    path('events/<int:event_pk>/export/', feature_views.export_attendees, name='export_attendees'),
      # paypal payment
    path('events/<int:event_pk>/paypal/',         paypal_views.paypal_payment_page,    name='paypal_payment_page'),
    path('events/<int:event_pk>/paypal/create/',  paypal_views.create_paypal_order,    name='create_paypal_order'),
    path('events/<int:event_pk>/paypal/capture/', paypal_views.capture_paypal_payment, name='capture_paypal_payment'),


# saved ,users,follow urls
    path('organiser/<str:username>/',        next10_views.organiser_profile,   name='organiser_profile'),
    path('organiser/<str:username>/follow/', next10_views.follow_organizer,    name='follow_organizer'),
    path('events/<int:event_pk>/save/',      next10_views.toggle_save_event,   name='toggle_save_event'),
    path('saved/',                           next10_views.saved_events,         name='saved_events'),
    path('events/<int:event_pk>/viewers/',   next10_views.viewers_count,        name='viewers_count'),


# PDF ticket download
    path('tickets/<int:registration_pk>/pdf/', pdf_views.download_ticket_pdf, name='download_ticket_pdf'),

    # Promo code validation (AJAX)
    path('events/<int:event_pk>/promo/',       extra_views.validate_promo_code, name='validate_promo_code'),

    # Notifications
    path('notifications/',                     extra_views.notification_list,       name='notification_list'),
    path('notifications/count/',               extra_views.notification_count,      name='notification_count'),
    path('notifications/<int:notif_pk>/read/', extra_views.mark_notification_read,  name='mark_notification_read'),

    # Q&A
    path('events/<int:event_pk>/ask/',         extra_views.ask_question,    name='ask_question'),
    path('questions/<int:question_pk>/answer/',extra_views.answer_question,  name='answer_question'),

    # Review reply
    path('reviews/<int:review_pk>/reply/',     extra_views.reply_to_review,  name='reply_to_review'),

    # Organiser analytics
    path('events/<int:event_pk>/analytics/',   extra_views.organiser_analytics, name='organiser_analytics'),

    # Search autocomplete
    path('search/autocomplete/',               extra_views.search_autocomplete, name='search_autocomplete'),

    # Share link
    path('events/<int:event_pk>/share-link/',  extra_views.get_event_share_link, name='event_share_link'),
]

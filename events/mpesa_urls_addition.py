# Add these lines to your existing events/urls.py
# Inside the urlpatterns list

# ---- M-PESA PAYMENT URLS ----
# (import mpesa_views at the top of urls.py first)

"""
Add this import at the top of events/urls.py:
    from . import mpesa_views

Then add these paths to urlpatterns:
"""

MPESA_URL_PATTERNS = """
    # M-Pesa payment flow
    path('events/<int:event_pk>/pay/',        mpesa_views.payment_page,          name='payment_page'),
    path('events/<int:event_pk>/pay/start/',  mpesa_views.initiate_payment,      name='initiate_payment'),
    path('payment/waiting/<int:payment_id>/', mpesa_views.payment_waiting,       name='payment_waiting'),
    path('payment/status/<int:payment_id>/',  mpesa_views.check_payment_status,  name='check_payment_status'),
    path('payment/result/<int:payment_id>/',  mpesa_views.payment_result,        name='payment_result'),

    # Safaricom calls this URL with the payment result (must be public)
    path('mpesa/callback/', mpesa_views.mpesa_callback, name='mpesa_callback'),
"""

print(MPESA_URL_PATTERNS)

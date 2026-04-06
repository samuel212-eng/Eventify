# events/paypal_views.py
# =============================================
#  PayPal payment integration using PayPal's
#  standard REST API (no extra libraries needed)
#  Uses the sandbox for testing
# =============================================

import requests
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Event, Registration, MpesaPayment


def get_paypal_token():
    """
    Step 1: Ask PayPal for an access token.
    We send our client ID and secret, PayPal gives us a token.
    """
    response = requests.post(
        f"{settings.PAYPAL_BASE_URL}/v1/oauth2/token",
        headers={"Accept": "application/json"},
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET),
        data={"grant_type": "client_credentials"},
    )
    return response.json().get("access_token")


@login_required
def paypal_payment_page(request, event_pk):
    """Shows the PayPal payment option page"""
    event = get_object_or_404(Event, pk=event_pk, is_published=True)

    if event.price == 0:
        return redirect('event_register', pk=event_pk)

    if Registration.objects.filter(event=event, user=request.user).exists():
        messages.warning(request, "You're already registered for this event!")
        return redirect('event_detail', slug=event.slug)

    if event.is_full():
        messages.error(request, "Sorry, this event is fully booked.")
        return redirect('event_detail', slug=event.slug)

    return render(request, 'events/paypal_payment.html', {'event': event})


@login_required
def create_paypal_order(request, event_pk):
    """
    Step 2: Create a PayPal order.
    PayPal gives us an order ID and an approval URL.
    We send the user to that URL to approve the payment.
    """
    event = get_object_or_404(Event, pk=event_pk, is_published=True)
    token = get_paypal_token()

    # Build the order
    order_data = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {
                "currency_code": "USD",
                # Convert KES to USD (rough rate — use a live rate in production)
                "value": str(round(float(event.price) / 130, 2)),
            },
            "description": f"Ticket: {event.title[:120]}",
        }],
        "application_context": {
            # Where PayPal sends the user after they approve
            "return_url": request.build_absolute_uri(f"/events/{event_pk}/paypal/capture/"),
            # Where PayPal sends the user if they cancel
            "cancel_url": request.build_absolute_uri(f"/events/{event_pk}/paypal/"),
        }
    }

    response = requests.post(
        f"{settings.PAYPAL_BASE_URL}/v2/checkout/orders",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        json=order_data,
    )

    result = response.json()

    if result.get("status") == "CREATED":
        # Find the approval URL in the response links
        for link in result.get("links", []):
            if link["rel"] == "approve":
                # Send user to PayPal to log in and approve
                return redirect(link["href"])

    messages.error(request, "Could not connect to PayPal. Please try again.")
    return redirect('paypal_payment_page', event_pk=event_pk)


@login_required
def capture_paypal_payment(request, event_pk):
    """
    Step 3: User approved on PayPal and was sent back here.
    We capture (complete) the payment.
    """
    event    = get_object_or_404(Event, pk=event_pk)
    order_id = request.GET.get("token")   # PayPal puts the order ID in the URL

    if not order_id:
        messages.error(request, "Payment was cancelled.")
        return redirect('event_detail', slug=event.slug)

    token = get_paypal_token()

    # Tell PayPal to actually take the money
    response = requests.post(
        f"{settings.PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
    )

    result = response.json()

    if result.get("status") == "COMPLETED":
        # Payment worked — create the registration
        registration, created = Registration.objects.get_or_create(
            event=event,
            user=request.user,
            defaults={'phone': ''}
        )

        messages.success(request,
            f"✅ PayPal payment successful! You're registered for {event.title}. "
            f"Your check-in code is {registration.check_in_code}"
        )
        return redirect('my_tickets')

    messages.error(request, "Payment could not be completed. Please try again.")
    return redirect('paypal_payment_page', event_pk=event_pk)

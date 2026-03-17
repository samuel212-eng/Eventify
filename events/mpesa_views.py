# events/mpesa_views.py
# =============================================
#  Views that handle the M-Pesa payment flow.
#  Add these to your existing views.py file,
#  or keep them here and import them in urls.py
# =============================================

import json
from django.shortcuts        import render, get_object_or_404, redirect
from django.http             import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib          import messages

from .models import Event, Registration, MpesaPayment
from .mpesa   import stk_push, format_phone


# --------------------------------------------------
# STEP 1: Show the payment page
# --------------------------------------------------
@login_required
def payment_page(request, event_pk):
    """
    Shows the 'Enter your M-Pesa number' form.
    The user lands here after clicking Register on a paid event.
    """
    event = get_object_or_404(Event, pk=event_pk, is_published=True)

    # Don't show payment page for free events
    if event.price == 0:
        return redirect('event_register', pk=event_pk)

    # Don't let someone pay twice
    if Registration.objects.filter(event=event, user=request.user).exists():
        messages.warning(request, "You're already registered for this event!")
        return redirect('event_detail', pk=event_pk)

    if event.is_full():
        messages.error(request, "Sorry, this event is fully booked.")
        return redirect('event_detail', pk=event_pk)

    return render(request, 'events/payment.html', {'event': event})


# --------------------------------------------------
# STEP 2: Initiate the STK Push
# --------------------------------------------------
@login_required
def initiate_payment(request, event_pk):
    """
    Called when the user submits the payment form.
    We send the STK push and wait for Safaricom's callback.
    """
    if request.method != 'POST':
        return redirect('payment_page', event_pk=event_pk)

    event        = get_object_or_404(Event, pk=event_pk)
    phone_input  = request.POST.get('phone_number', '').strip()
    phone        = format_phone(phone_input)

    # Basic phone validation
    if len(phone) != 12 or not phone.startswith('254'):
        messages.error(request, "Please enter a valid Kenyan phone number.")
        return redirect('payment_page', event_pk=event_pk)

    # Create a Registration row (we'll keep it even if payment fails,
    # but the MpesaPayment.status tells us if they actually paid)
    registration, created = Registration.objects.get_or_create(
        event=event,
        user=request.user,
        defaults={'phone': phone_input}
    )

    # Get existing payment or create a new one
    # (prevents crash if user submits the form twice)
    payment, created = MpesaPayment.objects.get_or_create(
        registration=registration,
        defaults={
            'phone_number': phone,
            'amount': event.price,
        }
    )

    # If payment already exists and completed, don't restart it
    if not created and payment.status == MpesaPayment.COMPLETED:
        messages.success(request, "You've already paid for this event!")
        return redirect('my_tickets')

    # If it failed before, reset it so they can try again
    if not created and payment.status == MpesaPayment.FAILED:
        payment.phone_number = phone
        payment.status = MpesaPayment.PENDING
        payment.save()

    # Fire the STK push to Safaricom
    result = stk_push(
        phone_number      = phone,
        amount            = event.price,
        account_reference = "Eventify",
        description       = f"Payment for {event.title[:20]}",  # max 20 chars
    )

    # Safaricom returns ResponseCode '0' if the push was sent successfully
    if result.get('ResponseCode') == '0':
        # Save the checkout ID so we can match Safaricom's callback later
        payment.checkout_request_id = result.get('CheckoutRequestID', '')
        payment.save()

        # Send user to a "waiting" page
        return redirect('payment_waiting', payment_id=payment.pk)
    else:
        # Something went wrong before the phone even rang
        payment.status             = MpesaPayment.FAILED
        payment.result_description = result.get('errorMessage', 'STK push failed')
        payment.save()

        messages.error(request, f"Payment initiation failed: {payment.result_description}")
        return redirect('payment_page', event_pk=event_pk)


# --------------------------------------------------
# STEP 3: Waiting page (user is entering PIN on phone)
# --------------------------------------------------
@login_required
def payment_waiting(request, payment_id):
    """
    A simple page that tells the user to check their phone.
    It polls the server every 5 seconds to see if Safaricom has responded.
    """
    payment = get_object_or_404(MpesaPayment, pk=payment_id, registration__user=request.user)
    return render(request, 'events/payment_waiting.html', {'payment': payment})


# --------------------------------------------------
# STEP 3b: AJAX endpoint — "has the payment come through yet?"
# --------------------------------------------------
@login_required
def check_payment_status(request, payment_id):
    """
    The waiting page calls this every 5 seconds via JavaScript.
    Returns JSON so the page can update without a full reload.
    """
    payment = get_object_or_404(MpesaPayment, pk=payment_id, registration__user=request.user)

    return JsonResponse({
        'status':      payment.status,
        'receipt':     payment.mpesa_receipt_number,
        'description': payment.result_description,
    })


# --------------------------------------------------
# STEP 4: Safaricom's Callback (this is called by Safaricom, not the user)
# --------------------------------------------------
@csrf_exempt   # Safaricom can't send a CSRF token, so we must exempt this view
def mpesa_callback(request):
    """
    Safaricom POSTs the payment result to this URL.
    We find the matching payment, update its status, and save.

    This endpoint must be publicly accessible (use ngrok in development).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        # Parse the JSON body Safaricom sends
        data     = json.loads(request.body)
        callback = data['Body']['stkCallback']

        checkout_id  = callback['CheckoutRequestID']
        result_code  = callback['ResultCode']
        result_desc  = callback['ResultDesc']

        # Find our payment record by the checkout ID
        payment = MpesaPayment.objects.get(checkout_request_id=checkout_id)

        if result_code == 0:
            # Payment SUCCESS — dig out the receipt number from the metadata
            items = callback['CallbackMetadata']['Item']

            # The metadata is a list of {Name: ..., Value: ...} dicts
            meta = {item['Name']: item.get('Value', '') for item in items}

            payment.status               = MpesaPayment.COMPLETED
            payment.mpesa_receipt_number = str(meta.get('MpesaReceiptNumber', ''))
            payment.result_description   = result_desc

        else:
            # Payment FAILED (user cancelled, wrong PIN, insufficient funds, etc.)
            payment.status             = MpesaPayment.FAILED
            payment.result_description = result_desc

        payment.save()

    except MpesaPayment.DoesNotExist:
        # Safaricom sent a callback we don't have a record for — log and ignore
        pass
    except (KeyError, json.JSONDecodeError):
        # Malformed callback — ignore
        pass

    # Safaricom expects this exact response, otherwise it keeps retrying
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


# --------------------------------------------------
# STEP 5: Payment result page
# --------------------------------------------------
@login_required
def payment_result(request, payment_id):
    """Shows success or failure after payment is confirmed"""
    payment = get_object_or_404(MpesaPayment, pk=payment_id, registration__user=request.user)
    return render(request, 'events/payment_result.html', {'payment': payment})

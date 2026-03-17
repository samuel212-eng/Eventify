# M-Pesa Integration Setup Guide

Follow these steps in order. Don't skip any.

---

## Step 1 — Install the requests library

M-Pesa needs to make HTTP calls to Safaricom's servers.
Open your terminal and run:

```
pip install requests
```

---

## Step 2 — Get your Daraja API credentials

1. Go to https://developer.safaricom.co.ke
2. Create a free account (use any email)
3. Click **My Apps** → **Create New App**
4. Select **Lipa Na M-Pesa Sandbox**
5. Copy your **Consumer Key** and **Consumer Secret**

---

## Step 3 — Add settings to settings.py

Open `eventsite/settings.py` and paste at the very bottom:

```python
MPESA_CONSUMER_KEY    = 'your_consumer_key_here'
MPESA_CONSUMER_SECRET = 'your_consumer_secret_here'
MPESA_SHORTCODE       = '174379'   # default sandbox shortcode
MPESA_PASSKEY         = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
MPESA_CALLBACK_URL    = 'https://YOUR_NGROK_URL.ngrok.io/mpesa/callback/'
```

---

## Step 4 — Add the MpesaPayment model to models.py

Open `events/models.py` and paste the `MpesaPayment` class
from `mpesa_model_addition.py` at the bottom of the file.

Then run:
```
python manage.py makemigrations
python manage.py migrate
```

---

## Step 5 — Add the files

Copy these files into your `events/` folder:
- `mpesa.py`          (the API helper)
- `mpesa_views.py`    (the page logic)

---

## Step 6 — Update urls.py

Open `events/urls.py` and make it look like this:

```python
from django.urls import path
from . import views
from . import mpesa_views   # ADD THIS LINE

urlpatterns = [
    # ... your existing URLs ...

    # M-Pesa
    path('events/<int:event_pk>/pay/',        mpesa_views.payment_page,         name='payment_page'),
    path('events/<int:event_pk>/pay/start/',  mpesa_views.initiate_payment,     name='initiate_payment'),
    path('payment/waiting/<int:payment_id>/', mpesa_views.payment_waiting,      name='payment_waiting'),
    path('payment/status/<int:payment_id>/',  mpesa_views.check_payment_status, name='check_payment_status'),
    path('mpesa/callback/',                   mpesa_views.mpesa_callback,       name='mpesa_callback'),
]
```

---

## Step 7 — Update the event detail template

In `event_detail.html`, find the "Register Now" button and change it so
paid events go to the payment page instead:

```html
{% if event.price == 0 %}
    <a href="{% url 'event_register' event.pk %}" class="btn btn-brand w-100">
        Register (Free)
    </a>
{% else %}
    <a href="{% url 'payment_page' event_pk=event.pk %}" class="btn btn-brand w-100"
       style="background:linear-gradient(135deg,#00963A,#007A30);">
        <i class="bi bi-phone me-1"></i> Pay KES {{ event.price }}
    </a>
{% endif %}
```

---

## Step 8 — Set up ngrok (for the callback)

Safaricom needs to send the payment result to a public URL.
During development, ngrok creates a tunnel from the internet to your laptop.

1. Download ngrok from https://ngrok.com (free account)
2. Run your Django server: `python manage.py runserver`
3. In a second terminal: `ngrok http 8000`
4. Copy the https URL ngrok gives you (e.g. https://abc123.ngrok.io)
5. Update `MPESA_CALLBACK_URL` in settings.py:
   `'https://abc123.ngrok.io/mpesa/callback/'`

---

## Step 9 — Test with sandbox

Safaricom's sandbox has test phone numbers that simulate M-Pesa.
Use phone number **254708374149** with PIN **1234** to test.

The STK push won't go to a real phone in sandbox mode —
instead check the Daraja portal to see the simulated result.

---

## Going to Production

When you're ready to accept real money:

1. Apply for a **Go Live** on the Daraja portal (Safaricom reviews your app)
2. Get your real **Shortcode**, **Consumer Key**, **Consumer Secret**, and **Passkey**
3. In `mpesa.py`, change the sandbox URLs to production:
   - `sandbox.safaricom.co.ke` → `api.safaricom.co.ke`
4. Set your real server URL as `MPESA_CALLBACK_URL`
5. Store all secrets in environment variables, NOT directly in settings.py

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `400 Bad Request` | Wrong phone format | Use format 2547XXXXXXXX |
| `Invalid Access Token` | Wrong consumer key/secret | Double-check credentials |
| `CallBackURL not valid` | Safaricom can't reach your server | Check ngrok is running |
| `The transaction amount is less than the minimum` | Amount below 1 KES | Set a minimum price |
| `Request cancelled by user` | User dismissed the prompt | Show retry button |

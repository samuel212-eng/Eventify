# events/mpesa.py
# =============================================
#  All the M-Pesa API logic lives here.
#  This file talks to Safaricom's Daraja API.
#  Your views just call the functions here.
# =============================================

import requests
import base64
from datetime import datetime
from django.conf import settings


def get_access_token():
    """
    Step 1: Ask Safaricom for a temporary access token.
    This token proves we are a registered app.
    It expires after 1 hour, so we fetch a fresh one each time.
    """

    # Combine our consumer key and secret, then encode in base64
    # (This is how Safaricom wants us to identify ourselves)
    credentials = f"{settings.MPESA_CONSUMER_KEY}:{settings.MPESA_CONSUMER_SECRET}"
    encoded     = base64.b64encode(credentials.encode()).decode()

    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    response = requests.get(
        url,
        headers={"Authorization": f"Basic {encoded}"}
    )

    # Pull the token out of Safaricom's response
    token = response.json().get("access_token")
    return token


def generate_password():
    """
    Safaricom requires a password that is:
    BusinessShortCode + PassKey + Timestamp  →  base64 encoded

    This is just their security format.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"

    password = base64.b64encode(raw.encode()).decode()

    return password, timestamp


def stk_push(phone_number, amount, account_reference, description):
    """
    The main function — sends a payment prompt to the user's phone.

    phone_number     : format 2547XXXXXXXX  (no + sign, no spaces)
    amount           : integer, e.g. 500
    account_reference: short label shown on the user's phone, e.g. "Eventify"
    description      : longer description, e.g. "Payment for Tech Summit"

    Returns Safaricom's full response as a dictionary.
    """

    token             = get_access_token()
    password, timestamp = generate_password()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password":          password,
        "Timestamp":         timestamp,
        "TransactionType":   "CustomerPayBillOnline",
        "Amount":            int(amount),         # Must be a whole number
        "PartyA":            phone_number,        # Who is paying
        "PartyB":            settings.MPESA_SHORTCODE,
        "PhoneNumber":       phone_number,        # Phone to send the prompt to
        "CallBackURL":       settings.MPESA_CALLBACK_URL,  # Where Safaricom sends the result
        "AccountReference":  account_reference,
        "TransactionDesc":   description,
    }

    response = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"}
    )

    return response.json()


def format_phone(raw_number):
    """
    Convert any Kenyan phone format to 2547XXXXXXXX

    Examples:
        0712345678   →  254712345678
        +254712345678 →  254712345678
        254712345678 →  254712345678  (already correct)
    """
    number = str(raw_number).strip().replace(" ", "").replace("-", "")

    if number.startswith("+"):
        number = number[1:]          # Remove the + sign

    if number.startswith("0"):
        number = "254" + number[1:]  # Replace leading 0 with 254

    return number

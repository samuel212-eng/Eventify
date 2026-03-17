# =============================================
#  Add these lines to the BOTTOM of your
#  eventsite/settings.py file
# =============================================

# ------ M-PESA / DARAJA API SETTINGS ------
# Get these from https://developer.safaricom.co.ke
# (Create a free account → go to My Apps → Create App)

# Your app's Consumer Key and Consumer Secret
MPESA_CONSUMER_KEY    = 'paste_your_consumer_key_here'
MPESA_CONSUMER_SECRET = 'paste_your_consumer_secret_here'

# The till number or paybill number for your sandbox app
# Default sandbox shortcode is 174379
MPESA_SHORTCODE = '174379'

# The Lipa Na M-Pesa Online PassKey
# Default sandbox passkey — get the real one from the Daraja portal
MPESA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'

# The URL Safaricom will POST the payment result to.
# During development: use ngrok to get a public URL
# Example: https://abc123.ngrok.io/mpesa/callback/
MPESA_CALLBACK_URL = 'https://YOUR_NGROK_URL.ngrok.io/mpesa/callback/'

# Switch to 'live' when going to production
# (also change sandbox URLs in mpesa.py to production URLs)
MPESA_ENV = 'sandbox'

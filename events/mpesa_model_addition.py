# Add these new classes to your existing events/models.py
# (paste them at the bottom, after your Registration model)


class MpesaPayment(models.Model):
    """
    Stores every M-Pesa payment attempt.
    We create one of these the moment the user clicks "Pay",
    then update it when Safaricom sends back the result.
    """

    # Payment statuses
    PENDING   = 'pending'
    COMPLETED = 'completed'
    FAILED    = 'failed'

    STATUS_CHOICES = [
        (PENDING,   'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED,    'Failed'),
    ]

    # Which registration this payment is for
    registration = models.OneToOneField(
        'Registration',
        on_delete=models.CASCADE,
        related_name='payment'
    )

    # The phone number that was charged (format: 2547XXXXXXXX)
    phone_number = models.CharField(max_length=15)

    # Amount charged
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Safaricom gives us this ID when we initiate the request
    # We use it to match the callback to the right payment
    checkout_request_id = models.CharField(max_length=200, blank=True)

    # Safaricom's own transaction ID (e.g. RCI71X58Y4)
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)

    # Current state of the payment
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)

    # Safaricom's response message
    result_description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.phone_number} | {self.amount} KES | {self.status}"

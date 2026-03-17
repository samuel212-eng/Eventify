# events/verification_forms.py

from django import forms
from .models import OrganizerProfile, EventReport


class OrganizerVerificationForm(forms.ModelForm):
    """
    The form an organiser fills in to get verified.
    Collects ID, selfie, phone number, and payout details.
    """
    class Meta:
        model  = OrganizerProfile
        fields = [
            'phone_number',
            'id_number',
            'id_document',
            'selfie_with_id',
            'organization_name',
            'website',
            'bio',
            'social_media',
            'mpesa_number',
        ]
        widgets = {
            'bio':               forms.Textarea(attrs={'rows': 4}),
            'phone_number':      forms.TextInput(attrs={'placeholder': '0712 345 678'}),
            'id_number':         forms.TextInput(attrs={'placeholder': 'e.g. 12345678'}),
            'organization_name': forms.TextInput(attrs={'placeholder': 'Optional — company or event brand name'}),
            'mpesa_number':      forms.TextInput(attrs={'placeholder': 'Number that will receive event payouts'}),
        }

    def clean_id_number(self):
        """Make sure the ID number hasn't been used by another account"""
        id_number = self.cleaned_data.get('id_number')
        existing  = OrganizerProfile.objects.filter(id_number=id_number)

        # If editing, exclude self
        if self.instance and self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)

        if existing.exists():
            raise forms.ValidationError(
                "This ID number is already associated with another account. "
                "Contact support if you think this is an error."
            )
        return id_number

    def clean_mpesa_number(self):
        """Format and validate the M-Pesa number"""
        number = self.cleaned_data.get('mpesa_number', '').replace(' ', '')
        if number.startswith('0'):
            number = '254' + number[1:]
        if not number.startswith('254') or len(number) != 12:
            raise forms.ValidationError("Enter a valid Kenyan M-Pesa number.")
        return number


class EventReportForm(forms.ModelForm):
    """Form for reporting a suspicious event"""
    class Meta:
        model  = EventReport
        fields = ['reason', 'details']
        widgets = {
            'details': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe what made you suspicious. Include any links or screenshots if possible.'
            }),
        }

# =============================================
#  Forms — the HTML forms users fill in
#  Django auto-generates these from our models
# =============================================

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Event, Registration


class SignUpForm(UserCreationForm):
    """Registration form with an extra email field"""
    email      = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=False)
    last_name  = forms.CharField(max_length=50, required=False)

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class EventForm(forms.ModelForm):
    """Form for creating or editing an event"""

    # Use a nice date-time picker in the browser
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
    )

    class Meta:
        model  = Event
        # Show these fields in the form (not organizer — we set that automatically)
        fields = ['title', 'description', 'category', 'date', 'location',
                  'image', 'price', 'capacity', 'is_published']

        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }


class RegistrationForm(forms.ModelForm):
    """Form for registering for an event"""

    class Meta:
        model  = Registration
        fields = ['phone', 'message']

        widgets = {
            'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any special requests?'}),
            'phone':   forms.TextInput(attrs={'placeholder': '+1 555 000 0000'}),
        }

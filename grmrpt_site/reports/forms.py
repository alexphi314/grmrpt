from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from reports.models import BMGUser, Resort


class SignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class BMGUserCreationForm(forms.Form):
    phone = forms.CharField(help_text='Required. Phone number to receive text alerts. +1XXX-XXX-XXXX')
    resorts = forms.MultipleChoiceField(help_text='Resorts you want to follow',
                                        choices=[(resort.name, resort) for resort in Resort.objects.all()])
    contact_method = forms.ChoiceField(help_text="How you wish to receive notifications",
                                       choices=[('EM', 'Email'), ('PH', 'Phone')])
    contact_days = forms.MultipleChoiceField(help_text='Days when you want to be notified',
                                             choices=[('Sun', 'Sunday'),
                                                      ('Mon', 'Monday'),
                                                      ('Tue', 'Tuesday'),
                                                      ('Wed', 'Wednesday'),
                                                      ('Thu', 'Thursday'),
                                                      ('Fri', 'Friday'),
                                                      ('Sat', 'Saturday')])

    class Meta:
        model = BMGUser
        fields = ['phone', 'resorts', 'contact_method', 'contact_days']



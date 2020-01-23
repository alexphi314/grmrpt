import json
from json.decoder import JSONDecodeError

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from reports.models import BMGUser, Resort, phone_regex


class SignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class UpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    email = forms.EmailField(max_length=254, help_text='Required. Inform a valid email address.')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class JsonCheckboxSelectMultiple(forms.CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, renderer=None):
        try:
            value = json.loads(value.replace('\'', '\"'))
        except (AttributeError, JSONDecodeError):
            pass

        return super().render(name, value, attrs, renderer)


class BMGUserCreationUpdateForm(forms.ModelForm):
    phone = forms.CharField(help_text='Required. Phone number to receive text alerts. +1XXXXXXXXXX',
                            validators=[phone_regex], max_length=17)
    resorts = forms.ModelMultipleChoiceField(help_text='Optional. Resorts you want to follow',
                                             required=False,
                                             queryset=Resort.objects.all(),
                                             to_field_name='name',
                                             widget=forms.CheckboxSelectMultiple())
    contact_method = forms.ChoiceField(help_text="Required. How you wish to receive notifications",
                                       required=True,
                                       choices=[('EM', 'Email'), ('PH', 'Phone')])
    contact_days = forms.MultipleChoiceField(help_text='Required. Days when you want to be notified',
                                             choices=[("Sun", 'Sunday'),
                                                      ("Mon", 'Monday'),
                                                      ("Tue", 'Tuesday'),
                                                      ("Wed", 'Wednesday'),
                                                      ("Thu", 'Thursday'),
                                                      ("Fri", 'Friday'),
                                                      ("Sat", 'Saturday')],
                                             required=True,
                                             widget=JsonCheckboxSelectMultiple())

    def save(self, commit=True) -> BMGUser:
        """
        Overload the saving method. Perform pre-save formatting then save the instance.

        :param commit: True if the posted data is being saved to the db
        :return: the BMGUser instance
        """
        self.instance.contact_days = self.instance.contact_days.replace('\'', '\"')
        self.instance.phone = self.instance.phone.replace('-', '')

        return super().save(commit)

    class Meta:
        model = BMGUser
        fields = ['phone', 'resorts', 'contact_method', 'contact_days']



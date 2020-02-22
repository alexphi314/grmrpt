import json
from json.decoder import JSONDecodeError
from typing import Union, List

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from reports.models import BMGUser, Resort, phone_regex


def email_validator(value: str) -> None:
    """
    Check the input email is unique, or raise a Validation Error

    :param value: input email
    :return: None if no error; ValidationError if there is a similar email in the DB
    """
    existing_emails = [user.email for user in User.objects.all()]
    if value in existing_emails:
        raise ValidationError(
            '{} is already connected to another user.'.format(value)
        )


class SignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.', label='First Name')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.', label='Last Name')
    email = forms.EmailField(max_length=254, help_text='Required. Submit a valid email address.',
                             validators=[email_validator])

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']


class UpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.', label='First Name')
    last_name = forms.CharField(max_length=30, required=False, help_text='Optional.', label='Last Name')
    email = forms.EmailField(max_length=254, help_text='Required. Submit a valid email address.')

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
                            validators=[phone_regex], max_length=17,
                            label='Phone Number')
    resorts = forms.ModelMultipleChoiceField(help_text='Optional. Select the resorts you want to get reports for',
                                             required=False,
                                             queryset=Resort.objects.all(),
                                             to_field_name='name',
                                             widget=forms.CheckboxSelectMultiple(),
                                             label='Resorts')
    contact_method = forms.ChoiceField(help_text="Required if resorts are selected. "
                                                 "How you wish to receive notifications",
                                       required=False,
                                       choices=[('EM', 'Email'), ('PH', 'SMS')],
                                       label='Contact Method')
    contact_days = forms.MultipleChoiceField(help_text='Required if resorts are selected. '
                                                       'Days when you want to receive reports',
                                             choices=[("Sun", 'Sunday'),
                                                      ("Mon", 'Monday'),
                                                      ("Tue", 'Tuesday'),
                                                      ("Wed", 'Wednesday'),
                                                      ("Thu", 'Thursday'),
                                                      ("Fri", 'Friday'),
                                                      ("Sat", 'Saturday')],
                                             required=False,
                                             widget=JsonCheckboxSelectMultiple(),
                                             label='Contact Days')

    def save(self, commit=True) -> BMGUser:
        """
        Overload the saving method. Perform pre-save formatting then save the instance.

        :param commit: True if the posted data is being saved to the db
        :return: the BMGUser instance
        """
        if isinstance(self.instance.contact_days, list):
            self.instance.contact_days = "[]"
        else:
            self.instance.contact_days = self.instance.contact_days.replace('\'', '\"')
        self.instance.phone = self.instance.phone.replace('-', '')

        return super().save(commit)

    def required_fields(self, fields: List[str], trigger_field: str) -> None:
        """
        For each field given, raise a ValidationError if the field is not provided

        :param fields: list of field names that are required
        :param trigger_field: the provided field in the form making the fields list required fields
        """
        for field in fields:
            data = self.cleaned_data.get(field, None)
            if data is None or (isinstance(data, list) and len(data) == 0):
                msg = forms.ValidationError("This field is required as {} is selected.".format(trigger_field))
                self.add_error(field, msg)

    def clean(self):
        """
        Overload the default clean method. Perform form field validation -> enforce fields required if Resorts is not
        empty
        """
        resorts = self.cleaned_data['resorts']

        if resorts:
            self.required_fields(['contact_method', 'contact_days'], 'resorts')

        return super().clean()

    class Meta:
        model = BMGUser
        fields = ['phone', 'resorts', 'contact_method', 'contact_days']

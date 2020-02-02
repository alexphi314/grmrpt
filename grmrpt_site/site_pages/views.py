from django.contrib.auth.models import User
from django.contrib.auth import logout, login
from django.shortcuts import render
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse as django_reverse

from reports.models import Resort
from site_pages.forms import BMGUserCreationUpdateForm, SignupForm, UpdateForm
from grmrptcore.settings import LOGIN_REDIRECT_URL


def create_update_user(request, UserForm, user=None):
    """
    Create or update a user instance in the db based on input forms

    :param request: input request
    :param UserForm: which user form to use
    :param user: optionally provided logged in user
    :return: HttpResponse of some sort
    """
    if user is None:
        user_form = UserForm(request.POST)
        bmg_user_form = BMGUserCreationUpdateForm(request.POST)
        alert_str = 'New user created successfully'.replace(' ', '_')
    else:
        user_form = UserForm(request.POST, instance=user)
        bmg_user_form = BMGUserCreationUpdateForm(request.POST, instance=user.bmg_user)
        alert_str = 'Profile updated successfully'.replace(' ', '_')

    if user_form.is_valid() and bmg_user_form.is_valid():
        user = user_form.save()
        user.refresh_from_db()  # This will load the Profile created by the Signal
        bmg_form = BMGUserCreationUpdateForm(request.POST, instance=user.bmg_user)
        bmg_form.full_clean()  # Manually clean the form this time
        bmg_form.save()  # Gracefully save the form

        # Log the user in
        login(request, user)

        url = django_reverse('profile-alert', kwargs={'alert': alert_str})
        return HttpResponseRedirect(url)
    else:

        # Load form showing errors
        return render(request, 'signup.html', {
            'forms': [user_form, bmg_user_form],
            'button_label': 'Sign Up',
            'title': 'Sign Up',
            'error': 'True'
        })


@transaction.atomic
def create_user(request):
    if request.method == 'POST':
        return create_update_user(request, SignupForm)
    else:
        if request.user.is_authenticated:
            return HttpResponseRedirect(django_reverse('profile'))

        user_form = SignupForm()
        bmg_user_form = BMGUserCreationUpdateForm()

    return render(request, 'signup.html', {
        'forms': [user_form, bmg_user_form],
        'button_label': 'Sign Up',
        'title': 'Sign Up'
    })


@transaction.atomic
def profile_view(request, alert=''):
    if request.method == 'GET':
        if not request.user.is_authenticated:
            return HttpResponseRedirect(django_reverse('login'))

        user = request.user
        user_form = UpdateForm(instance=user)
        bmg_user_form = BMGUserCreationUpdateForm(instance=user.bmg_user)

        params = {}
        params['alert'] = alert.replace('_', ' ')
        params['forms'] = [user_form, bmg_user_form]
        params['button_label'] = 'Update'
        params['title'] = 'User Profile'
        return render(request, 'signup.html', params)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return HttpResponseRedirect(django_reverse('login'))

        return create_update_user(request, UpdateForm, request.user)


def logout_user(request):
    if request.method == 'GET':
        logout(request)

        return HttpResponseRedirect(LOGIN_REDIRECT_URL)


def index(request):
    if request.method == 'GET':
        num_resorts = Resort.objects.count()
        return render(request, 'index.html', {'resorts_str': ', and '.join([
            ', '.join([resort.name for resort in Resort.objects.all().order_by('id')[:num_resorts-1]]),
            Resort.objects.all()[num_resorts-1].name
        ])})
    else:
        return HttpResponseNotFound(request)


def contact_us(request):
    if request.method == 'GET':
        return render(request, 'contact_us.html', {})
    else:
        return HttpResponseBadRequest()


def about(request):
    if request.method == 'GET':
        return render(request, 'about.html', {'resorts': [resort.name for resort in
                                                          Resort.objects.all().order_by('id')]})
    else:
        return HttpResponseBadRequest()


def delete(request):
    if request.method == 'GET':
        if not request.user.is_authenticated:
            return HttpResponseRedirect(django_reverse('signup'))

        user = User.objects.get(username=request.user)
        logout(request)
        user.delete()

        return render(request, 'deleted.html')

    else:
        return HttpResponseBadRequest()

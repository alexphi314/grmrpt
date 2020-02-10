from django.contrib.auth.models import User
from django.contrib.auth import logout, login
from django.shortcuts import render
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponseNotFound
from django.urls import reverse as django_reverse
from django.contrib.auth.decorators import login_required

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
    """
    Render the create user view (form)

    :param request: http request
    :return: rendered html template
    """
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
@login_required()
def profile_view(request, alert=''):
    """
    Show a user's profile and update if requested

    :param request: http request
    :param alert: alert text to show in an alert box at top of page, if given
    :return: rendered html template
    """
    if request.method == 'GET':
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
            return HttpResponseRedirect(django_reverse('login-next', kwargs={'next': django_reverse('profile')}))

        return create_update_user(request, UpdateForm, request.user)


def logout_user(request):
    """
    logout the user

    :param request: http request
    :return: redirect to index
    """
    if request.method == 'GET':
        logout(request)

        return HttpResponseRedirect(LOGIN_REDIRECT_URL)


def index(request):
    """
    Load the home page

    :param request: http request
    :return: rendered home page
    """
    if request.method == 'GET':
        num_resorts = Resort.objects.count()
        return render(request, 'index.html', {'resorts_str': ', and '.join([
            ', '.join([resort.name for resort in Resort.objects.all().order_by('id')[:num_resorts-1]]),
            Resort.objects.all()[num_resorts-1].name
        ])})
    else:
        return HttpResponseNotFound(request)


def contact_us(request):
    """
    Load the contact us page

    :param request: http request
    :return: rendered page
    """
    if request.method == 'GET':
        return render(request, 'contact_us.html', {})
    else:
        return HttpResponseBadRequest()


def about(request):
    """
    Load the about/faq page

    :param request: http request
    :return: rendered page
    """
    if request.method == 'GET':
        return render(request, 'about.html', {'resorts': [resort.name for resort in
                                                          Resort.objects.all().order_by('id')]})
    else:
        return HttpResponseBadRequest()


def delete(request):
    """
    Delete the logged-in user from the DB

    :param request: http request
    :return: rendered delete page
    """
    if request.method == 'GET':
        if not request.user.is_authenticated:
            return HttpResponseRedirect(django_reverse('login'))

        user = User.objects.get(username=request.user)
        logout(request)
        user.delete()

        return render(request, 'deleted.html')

    else:
        return HttpResponseBadRequest()

@login_required()
def reports(request):
    """
    Load the most recent BMReport for each resort

    :param request: http request
    :return: rendered reports page
    """
    if request.method == 'GET':
        resorts = Resort.objects.all()
        # Get the most recent BMReport for each resort
        most_recent_reports = [resort.bm_reports.all()[resort.bm_reports.count()-1] for resort in resorts if
                               resort.bm_reports.count() > 0]

        # Make a list of run names for each report
        report_runs = [
            [run.name for run in report.runs.all()]
            for report in most_recent_reports
        ]

        # Create a master list with resort name, report date, report url, and run list
        reports_runs = []
        for indx, report_run in enumerate(report_runs):
            if resorts[indx].display_url is None or resorts[indx].display_url == '':
                url = resorts[indx].report_url
            else:
                url = resorts[indx].display_url

            reports_runs.append([resorts[indx].name, most_recent_reports[indx].date.strftime('%b %d, %Y'),
                                 url, report_run])

        # Group the reports and runs into groups of 2
        # The two groups are put next to each other on the site
        num_reports = 2
        reports_runs_grouped = [
            reports_runs[i:i+num_reports] for i in range(0, len(reports_runs), num_reports)
        ]

        return render(
            request,
            'reports.html',
            {
                'resorts_runs': reports_runs_grouped
            }
        )

    else:
        return HttpResponseBadRequest()

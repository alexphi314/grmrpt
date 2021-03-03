from collections import Counter
import io
import datetime as dt

from django.contrib.auth.models import User
from django.contrib.auth import logout, login
from django.shortcuts import render
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django.urls import reverse as django_reverse
from django.contrib.auth.decorators import login_required
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

from reports.models import Resort, Run
from site_pages.forms import BMGUserCreationUpdateForm, SignupForm, UpdateForm
from grmrptcore.settings import LOGIN_REDIRECT_URL


def create_update_user(request, UserForm, user=None, title: str='Sign Up', button_label: str='Sign Up'):
    """
    Create or update a user instance in the db based on input forms

    :param request: input request
    :param UserForm: which user form to use
    :param user: optionally provided logged in user
    :param title: page title
    :param button_label: label for button at bottom
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
            'button_label': button_label,
            'title': title,
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

        return create_update_user(request, UpdateForm, request.user, title='User Profile', button_label='Update')


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

        resorts_str = 'Coming Soon' if num_resorts == 0 else ', and '.join([
            ', '.join([resort.name for resort in Resort.objects.all().order_by('id')[:num_resorts-1]]),
            Resort.objects.all()[num_resorts-1].name
        ])
        return render(request, 'index.html', {'resorts_str': resorts_str})
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
            [[run.name, '/runs/{}'.format(run.id), 'difficulty_images/{}.png'.format(run.difficulty)
                                                   if run.difficulty is not None else None
              ]
             for run in report.runs.all()]
            for report in most_recent_reports
        ]

        # Create a master list with resort name, report date, report url, and run list
        resort_report_run_list = []
        for indx, report_run in enumerate(report_runs):
            if resorts[indx].display_url is None or len(resorts[indx].display_url) == 0:
                url = resorts[indx].report_url
            else:
                url = resorts[indx].display_url

            resort_report_run_list.append([resorts[indx].name, most_recent_reports[indx].date.strftime('%b %d, %Y'),
                                           url, report_run])

        # Group the reports and runs into groups of 2
        # The two groups are put next to each other on the site
        num_reports = 2
        reports_runs_grouped = [
            resort_report_run_list[i:i+num_reports] for i in range(0, len(resort_report_run_list), num_reports)
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


@login_required()
def run_stats_img(request, run_id: int) -> HttpResponse:
    """
    Plot the stats of a specific run

    :param request: http request
    :param run_id: run record ID in db
    :return: image as HttpResponse
    """
    run = Run.objects.get(id=run_id)
    f = plt.figure()
    FigureCanvasAgg(f)

    # Calculate DoW distro
    dow = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    dow_array = [rpt.date.strftime('%a') for rpt in run.reports.all()]
    dow_dict = Counter(dow_array)

    # Create data array for plotting including all days of week
    dow_data = [
        dow_dict.get(day, 0) for day in dow
    ]

    plt.plot(dow, dow_data)
    plt.ylabel('Number of Grooms')
    plt.title('Grooming Frequency Per Day of Week')
    plt.tight_layout()

    # Generate canvas and return
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(f)
    response = HttpResponse(buf.getvalue(), content_type='image/png')

    return response


@login_required()
def run_stats(request, run_id: int):
    """
    Display season stats for a specific run

    :param request: http request
    :param run_id: run record ID in db
    :return: rendered html page
    """
    run = Run.objects.get(id=run_id)

    num_reports = run.reports.filter(date__gte=dt.datetime.now()-dt.timedelta(days=6*30)).count()
    num_bm_reports = run.bm_reports.filter(date__gte=dt.datetime.now()-dt.timedelta(days=6*30)).count()

    if num_bm_reports > 0:
        last_bm_report = run.bm_reports.all()[num_bm_reports-1].date.strftime('%a %b %d')
    else:
        last_bm_report = ''

    if num_reports > 0:
        last_report = run.reports.all()[num_reports-1].date.strftime('%a %b %d')
    else:
        last_report = ''

    # Get list of groom dates, tracking which were 'blue moon' days
    rpt_list = []
    bm_dates = [rpt.date for rpt in run.bm_reports.filter(date__gte=dt.datetime.now()-dt.timedelta(days=6*30)).all()]
    for rpt in run.reports.filter(date__gte=dt.datetime.now()-dt.timedelta(days=6*30)):
        if rpt.date in bm_dates:
            color = 'bm'
        else:
            color = ''

        rpt_list.append([rpt.date.strftime('%a %b %d'), color])

    params = {}
    params['num_reports'] = num_reports
    params['num_bm_reports'] = num_bm_reports
    params['last_bm_report'] = last_bm_report
    params['last_report'] = last_report
    params['plot_image'] = django_reverse('run-stats-plot', kwargs={'run_id': run_id})
    params['name'] = run.name
    params['rpt_list'] = rpt_list

    return render(
        request,
        'run_stats.html',
        params
    )




import datetime as dt

from django.contrib.auth.models import User
from django.contrib.auth import logout, login
from django.shortcuts import render
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponseRedirect, HttpResponseNotFound
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAdminUser

from reports.models import Report, Run, Resort, BMReport, BMGUser, Notification
from reports.serializers import ReportSerializer, RunSerializer, ResortSerializer, BMReportSerializer, \
    UserSerializer, BMGUserSerializer, NotificationSerializer
from reports.permissions import IsAdminOrReadOnly
from reports.forms import BMGUserCreationUpdateForm, SignupForm, UpdateForm
from grmrptcore.settings import LOGIN_REDIRECT_URL


@api_view(['GET'])
def api_root(request, format=None):
    """
    Define root view listing all data
    """
    return Response({
        'resorts': reverse('resort-list', request=request, format=format),
        'runs': reverse('run-list', request=request, format=format),
        'reports': reverse('report-list', request=request, format=format),
        'bm_reports': reverse('bmreport-list', request=request, format=format)
    })


class ResortList(generics.ListCreateAPIView):
    """
    Generic view showing all resorts
    """
    queryset = Resort.objects.all()
    serializer_class = ResortSerializer
    permission_classes = [IsAdminOrReadOnly]


class ResortDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view for specific resort
    """
    queryset = Resort.objects.all()
    serializer_class = ResortSerializer
    permission_classes = [IsAdminOrReadOnly]


class RunList(generics.ListCreateAPIView):
    """
    Generic view listing all runs
    """
    serializer_class = RunSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        """
        Find list of runs to display, filtered by optional fields

        :return: list of runs that match parameters (if given)
        """
        queryset = Run.objects.all()

        # If given, filter by resort name
        resort = self.request.query_params.get('resort', None)
        if resort is not None:
            queryset = queryset.filter(resort__name=resort)

        # If given, filter by run name
        name = self.request.query_params.get('name', None)
        if name is not None:
            queryset = queryset.filter(name=name)

        return queryset


class RunDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view listing specific run
    """
    queryset = Run.objects.all()
    serializer_class = RunSerializer
    permission_classes = [IsAdminOrReadOnly]


class ReportList(generics.ListCreateAPIView):
    """
    Generic view listing all reports
    """
    serializer_class = ReportSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        """
        Return objects in this list, based on optional filtering fields

        :return: list of report objects
        """
        queryset = Report.objects.all()

        # If given, filter by resort name
        resort = self.request.query_params.get('resort', None)
        if resort is not None:
            queryset = queryset.filter(resort__name=resort)

        # If given, filter by report date
        date = self.request.query_params.get('date', None)
        if date is not None:
            queryset = queryset.filter(date=dt.datetime.strptime(date, '%Y-%m-%d').date())

        return queryset


class ReportDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view listing specific report
    """
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAdminOrReadOnly]


class BMReportList(generics.ListCreateAPIView):
    """
    Generic view listing all bmreports
    """
    queryset = BMReport.objects.all()
    serializer_class = BMReportSerializer
    permission_classes = [IsAdminOrReadOnly]

    def post(self, request, *args, **kwargs):
        """
        Overload post method. BMReport objects are automatically created when a corresponding Report object is made.
        Thus is it not allowed to manually create them.
        """
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class BMReportDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view listing specific bmreport
    """
    queryset = BMReport.objects.all()
    serializer_class = BMReportSerializer
    permission_classes = [IsAdminOrReadOnly]

    def delete(self, request, *args, **kwargs):
        """
        Overload delete method. BMReport objects are tied to a Report object and should not be deleted.
        """
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class UserList(generics.ListCreateAPIView):
    """
    Generic view listing all users
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view for a specific user
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]


class BMGUserList(generics.ListCreateAPIView):
    """
    Generic view listing all BMGUsers
    """
    queryset = BMGUser.objects.all()
    serializer_class = BMGUserSerializer
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        """
        Overload POST method. This is an extension of User and should not be created from this end.
        """
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class BMGUserDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view for a specific BMGUser
    """
    queryset = BMGUser.objects.all()
    serializer_class = BMGUserSerializer
    permission_classes = [IsAdminUser]

    def delete(self, request, *args, **kwargs):
        """
        Overload DELETE method. This is an extension of User and should not be deleted from thsi end.
        """
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class NotificationList(generics.ListCreateAPIView):
    """
    Generic view listing all notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Return objects in this list, based on optional filtering fields

        :return: list of report objects
        """
        queryset = Notification.objects.all()

        # If given, filter by resort name
        resort = self.request.query_params.get('resort', None)
        if resort is not None:
            queryset = queryset.filter(bm_report__resort__name=resort)

        # If given, filter by report date
        date = self.request.query_params.get('report_date', None)
        if date is not None:
            queryset = queryset.filter(bm_report__date=dt.datetime.strptime(date, '%Y-%m-%d').date())

        # If given, filter by bm_report pk
        bm_pk = self.request.query_params.get('bm_pk', None)
        if bm_pk is not None:
            queryset = queryset.filter(bm_report__pk=bm_pk)

        return queryset


class NotificationDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view for a specific notification
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAdminUser]


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
    else:
        user_form = UserForm(request.POST, instance=user)
        bmg_user_form = BMGUserCreationUpdateForm(request.POST, instance=user.bmg_user)

    if user_form.is_valid() and bmg_user_form.is_valid():
        user = user_form.save()
        user.refresh_from_db()  # This will load the Profile created by the Signal
        bmg_form = BMGUserCreationUpdateForm(request.POST, instance=user.bmg_user)
        bmg_form.full_clean()  # Manually clean the form this time
        bmg_form.save()  # Gracefully save the form

        # Log the user in
        login(request, user)

        return HttpResponseRedirect('/profile')
    else:
        return HttpResponseBadRequest(content=[user_form.errors, bmg_user_form.errors])


@transaction.atomic
def create_user(request):
    if request.method == 'POST':
        return create_update_user(request, SignupForm)
    else:
        if request.user.is_authenticated:
            return HttpResponseRedirect('/profile')

        user_form = SignupForm()
        bmg_user_form = BMGUserCreationUpdateForm()

    return render(request, 'signup.html', {
        'forms': [user_form, bmg_user_form],
        'button_label': 'signup',
        'title': 'Sign Up'
    })


@transaction.atomic
def profile_view(request):
    if request.method == 'GET':
        if not request.user.is_authenticated:
            return HttpResponseRedirect('/login')

        user = request.user
        user_form = UpdateForm(instance=user)
        bmg_user_form = BMGUserCreationUpdateForm(instance=user.bmg_user)

        return render(request, 'signup.html', {
            'forms': [user_form, bmg_user_form],
            'button_label': 'update',
            'title': 'User Profile'
        })

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return HttpResponseRedirect('/login')

        return create_update_user(request, UpdateForm, request.user)


def logout_user(request):
    if request.method == 'GET':
        logout(request)

        return HttpResponseRedirect(LOGIN_REDIRECT_URL)


def index(request):
    if request.method == 'GET':
        num_resorts = Resort.objects.count()
        return render(request, 'index.html', {'resorts_str': ', and '.join([
            ', '.join([resort.name for resort in Resort.objects.all()[:num_resorts-1]]),
            Resort.objects.all()[num_resorts-1].name
        ])})
    else:
        return HttpResponseNotFound(request)


def contact_us(request):
    if request.method == 'GET':
        return render(request, 'contact_us.html', {})
    else:
        return HttpResponseBadRequest


def about(request):
    if request.method == 'GET':
        return render(request, 'about.html', {'resorts': [resort.name for resort in
                                                          Resort.objects.all()]})
    else:
        return HttpResponseBadRequest

import datetime as dt

from django.contrib.auth.models import User
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAdminUser

from reports.models import *
from reports.serializers import *
from reports.permissions import IsAdminOrReadOnly


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
    queryset = Resort.objects.all().order_by('id')
    serializer_class = ResortSerializer
    permission_classes = [IsAdminUser]


class ResortDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view for specific resort
    """
    queryset = Resort.objects.all().order_by('id')
    serializer_class = ResortSerializer
    permission_classes = [IsAdminUser]


class RunList(generics.ListCreateAPIView):
    """
    Generic view listing all runs
    """
    serializer_class = RunSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Find list of runs to display, filtered by optional fields

        :return: list of runs that match parameters (if given)
        """
        queryset = Run.objects.all().order_by('id')

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
    queryset = Run.objects.all().order_by('id')
    serializer_class = RunSerializer
    permission_classes = [IsAdminUser]


class ReportList(generics.ListCreateAPIView):
    """
    Generic view listing all reports
    """
    serializer_class = ReportSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Return objects in this list, based on optional filtering fields

        :return: list of report objects
        """
        queryset = Report.objects.all().order_by('id')

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
    queryset = Report.objects.all().order_by('id')
    serializer_class = ReportSerializer
    permission_classes = [IsAdminUser]


class BMReportList(generics.ListCreateAPIView):
    """
    Generic view listing all bmreports
    """
    queryset = BMReport.objects.all().order_by('id')
    serializer_class = BMReportSerializer
    permission_classes = [IsAdminUser]

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
    queryset = BMReport.objects.all().order_by('id')
    serializer_class = BMReportSerializer
    permission_classes = [IsAdminUser]

    def delete(self, request, *args, **kwargs):
        """
        Overload delete method. BMReport objects are tied to a Report object and should not be deleted.
        """
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class UserList(generics.ListCreateAPIView):
    """
    Generic view listing all users
    """
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view for a specific user
    """
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]


class BMGUserList(generics.ListCreateAPIView):
    """
    Generic view listing all BMGUsers
    """
    queryset = BMGUser.objects.all().order_by('id')
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
    queryset = BMGUser.objects.all().order_by('id')
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
        queryset = Notification.objects.all().order_by('id')

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
    queryset = Notification.objects.all().order_by('id')
    serializer_class = NotificationSerializer
    permission_classes = [IsAdminUser]


class AlertList(generics.ListCreateAPIView):
    """
    List view for alerts
    """
    serializer_class = AlertSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Return objects in this list, based on optional filtering fields

        :return: list of report objects
        """
        queryset = Alert.objects.all().order_by('id')

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


class AlertDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view for one alert
    """
    queryset = Alert.objects.all().order_by('id')
    serializer_class = AlertSerializer
    permission_classes = [IsAdminUser]

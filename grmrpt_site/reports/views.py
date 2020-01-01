import datetime as dt

from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics

from reports.models import Report, Run, Resort
from reports.serializers import ReportSerializer, RunSerializer, ResortSerializer


class ResortList(generics.ListCreateAPIView):
    """
    Generic view showing all resorts
    """
    queryset = Resort.objects.all()
    serializer_class = ResortSerializer


class ResortDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view for specific resort
    """
    queryset = Resort.objects.all()
    serializer_class = ResortSerializer


class RunList(generics.ListCreateAPIView):
    """
    Generic view listing all runs
    """
    serializer_class = RunSerializer

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


class ReportList(generics.ListCreateAPIView):
    """
    Generic view listing all reports
    """
    serializer_class = ReportSerializer

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

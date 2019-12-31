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
    queryset = Run.objects.all()
    serializer_class = RunSerializer


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
    queryset = Report.objects.all()
    serializer_class = ReportSerializer


class ReportDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view listing specific report
    """
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

import datetime as dt
from typing import List, Dict

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse

from reports.models import Report, Run, Resort, HDReport
from reports.serializers import ReportSerializer, RunSerializer, ResortSerializer, HDReportSerializer


@api_view(['GET'])
def api_root(request, format=None):
    """
    Define root view listing all data
    """
    return Response({
        'resorts': reverse('resort-list', request=request, format=format),
        'runs': reverse('run-list', request=request, format=format),
        'reports': reverse('report-list', request=request, format=format),
        'hd_reports': reverse('hdreport-list', request=request, format=format)
    })

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


def get_hd_runs(data: Dict, groomed_runs: List[Run]) -> List[Run]:
    """
    Extract the hidden diamond runs from the current report data, based on past data. Return the runs that were
    groomed today that have been groomed less than 90% of the past 7 days.

    :param data: current report validated data
    :param groomed_runs: run objects that were groomed today
    :return: list of hidden diamond run objects
    """
    # Get past reports for the last 7 days
    date = data['date']
    resort = data['resort']
    past_reports = Report.objects.filter(date__lt=date, date__gt=(date - dt.timedelta(days=8)),
                                         resort=resort)

    # If enough past reports, compare runs between reports and create HDReport
    hdreport_runs = []
    if len(past_reports) > 0:
        # Look at each run in today's report
        for run in groomed_runs:
            num_shared_reports = len(list(set(run.reports.all()).intersection(past_reports)))
            if float(num_shared_reports) / float(len(past_reports)) < 0.9:
                hdreport_runs.append(run)

    return hdreport_runs

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

    def perform_create(self, serializer: ReportSerializer) -> None:
        """
        Overload perform_create method. Use ReportSerializer to build HDReport object (if possible)

        :param serializer: input serializer with data for the report object
        """
        report = serializer.save()
        data = serializer.validated_data

        date = data['date']
        resort = data['resort']
        hdreport_runs = get_hd_runs(data, report.runs.all())

        hd_report = HDReport.objects.create(date=date, resort=resort, full_report=report)
        hd_report.runs.set(hdreport_runs)


class ReportDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view listing specific report
    """
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    def perform_update(self, serializer: ReportSerializer) -> None:
        """
        Overload perform_update method. Use ReportSerializer to update corresponding HDReport object as this object
        is updated

        :param serializer: input serializer with data for this report object
        """
        report = serializer.save()
        data = serializer.validated_data

        # Update the corresponding HDReport object
        date = data['date']
        resort = data['resort']
        hdreport_runs = get_hd_runs(data, report.runs.all())

        hd_report = report.hd_report
        hd_report.date = date
        hd_report.resort = resort
        hd_report.save()
        hd_report.runs.set(hdreport_runs)


class HDReportList(generics.ListCreateAPIView):
    """
    Generic view listing all hdreports
    """
    queryset = HDReport.objects.all()
    serializer_class = HDReportSerializer

    def post(self, request, *args, **kwargs):
        """
        Overload post method. HDReport objects are automatically created when a corresponding Report object is made.
        Thus is it not allowed to manually create them.
        """
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class HDReportDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Detailed view listing specific hdreport
    """
    queryset = HDReport.objects.all()
    serializer_class = HDReportSerializer

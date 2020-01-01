from rest_framework import serializers
from reports.models import *


class ResortSerializer(serializers.ModelSerializer):
    """
    Serializer for resort model
    """
    class Meta:
        model = Resort
        fields = ['name', 'location', 'report_url', 'id']


class RunSerializer(serializers.ModelSerializer):
    """
    Serializer for run model
    """
    resort = serializers.HyperlinkedRelatedField(many=False, view_name='resort-detail',
                                                 queryset=Resort.objects.all())
    reports = serializers.HyperlinkedRelatedField(many=True, view_name='report-detail',
                                                  queryset=Report.objects.all())

    class Meta:
        model = Run
        fields = ['name', 'difficulty', 'id', 'resort', 'reports']


class ReportSerializer(serializers.ModelSerializer):
    """
    Serializer for report model
    """
    resort = serializers.HyperlinkedRelatedField(many=False, view_name='resort-detail',
                                                 queryset=Resort.objects.all())
    runs = serializers.HyperlinkedRelatedField(many=True, view_name='run-detail',
                                               queryset=Run.objects.all())

    class Meta:
        model = Report
        fields = ['date', 'resort', 'runs', 'id']


class HDReportSerializer(ReportSerializer):
    """
    Serializer for HDreport model
    """

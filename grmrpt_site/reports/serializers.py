from rest_framework import serializers
from reports.models import *


class ResortSerializer(serializers.ModelSerializer):
    """
    Serializer for resort model
    """
    class Meta:
        model = Resort
        fields = ['name', 'location']


class ReportSerializer(serializers.ModelSerializer):
    """
    Serializer for report model
    """
    class Meta:
        model = Report
        fields = ['date', 'resort', 'run_set']


class RunSerializer(serializers.ModelSerializer):
    """
    Serializer for run model
    """
    class Meta:
        model = Run
        fields = ['name', 'difficulty', 'resort']


class HDReportSerializer(serializers.ModelSerializer):
    """
    Serializer for HDreport model
    """
    class Meta:
        model = HDReport
        fields = ['date', 'resort', 'runs']

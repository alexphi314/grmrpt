from rest_framework import serializers
from reports.models import *


class ResortSerializer(serializers.ModelSerializer):
    """
    Serializer for resort model
    """
    sns_arn = serializers.CharField(read_only=True)

    class Meta:
        model = Resort
        fields = ['name', 'location', 'report_url', 'id', 'sns_arn', 'parse_mode', 'display_url']


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
    bm_report = serializers.HyperlinkedRelatedField(many=False, view_name='bmreport-detail',
                                                    read_only=True)

    class Meta:
        model = Report
        fields = ['date', 'resort', 'runs', 'id', 'bm_report']


class BMReportSerializer(serializers.ModelSerializer):
    """
    Serializer for HDreport model
    """
    resort = serializers.HyperlinkedRelatedField(many=False, view_name='resort-detail',
                                                 queryset=Resort.objects.all())
    runs = serializers.HyperlinkedRelatedField(many=True, view_name='run-detail',
                                               queryset=Run.objects.all())
    full_report = serializers.HyperlinkedRelatedField(many=False, view_name='report-detail',
                                                      queryset=Report.objects.all())
    notification = serializers.HyperlinkedRelatedField(many=False, view_name='notification-detail',
                                                       read_only=True)

    class Meta:
        model = BMReport
        fields = ['date', 'resort', 'runs', 'id', 'full_report', 'notification']


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model
    """
    bmg_user = serializers.HyperlinkedRelatedField(many=False, view_name='bmguser-detail', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'bmg_user', 'is_staff']


class BMGUserSerializer(serializers.ModelSerializer):
    """
    Serializer for BMGUser model
    """
    user = UserSerializer(read_only=True)
    favorite_runs = serializers.HyperlinkedRelatedField(many=True, view_name='run-detail',
                                                        queryset=Run.objects.all())
    resorts = serializers.HyperlinkedRelatedField(many=True, view_name='resort-detail',
                                                  queryset=Resort.objects.all())
    sub_arn = serializers.CharField(read_only=True)

    class Meta:
        model = BMGUser
        fields = ['id', 'phone', 'user', 'favorite_runs', 'resorts', 'contact_method', 'sub_arn',
                  'contact_days']


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for notification model
    """
    bm_report = serializers.HyperlinkedRelatedField(many=False, view_name='bmreport-detail',
                                                    queryset=BMReport.objects.all())

    class Meta:
        model = Notification
        fields = ['id', 'bm_report', 'sent', 'type']

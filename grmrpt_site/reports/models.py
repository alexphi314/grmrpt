import datetime as dt
from typing import List, Union
import logging

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


class Resort(models.Model):
    """
    Ski resort model
    """
    name = models.CharField("Name of the resort", max_length=1000)
    location = models.CharField("Location of the resort", max_length=1000, blank=True, null=True)
    report_url = models.CharField("URL to grooming report", max_length=2000, blank=True, null=True)

    def __str__(self) -> str:
        return self.name


class Report(models.Model):
    """
    Object model for grooming report
    """
    date = models.DateField("Date of Grooming Report")
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='reports')

    def __str__(self) -> str:
        return '{}: {}'.format(self.resort, self.date.strftime('%Y-%m-%d'))


class Run(models.Model):
    """
    Object model for ski run
    """
    name = models.CharField("Name of the run", max_length=1000)
    difficulty = models.CharField("Difficulty of run, green/blue/black", max_length=100, blank=True, null=True)
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='runs')
    reports = models.ManyToManyField(Report, related_name='runs')

    def __str__(self) -> str:
        return self.name


class BMReport(models.Model):
    """
    Object model for processed Hidden Diamond grooming report
    """
    date = models.DateField("Date of Grooming Report")
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='bm_reports')
    runs = models.ManyToManyField(Run, related_name='bm_reports')
    full_report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='bm_report')

    def __str__(self) -> str:
        return '{}: {}'.format(self.resort, self.date.strftime('%Y-%m-%d'))


def get_bm_runs(report: Report) -> List[Run]:
    """
    Extract the blue moon runs from the current report data, based on past data. Return the runs that were
    groomed today that have been groomed less than 90% of the past 7 days.

    :param report: Report object bm_runs are pulled from
    :return: list of blue moon run objects
    """
    # Get logger
    logger = logging.getLogger(__name__)

    # Get past reports for the last 7 days
    date = report.date
    resort = report.resort
    past_reports = Report.objects.filter(date__lt=date, date__gt=(date - dt.timedelta(days=8)),
                                         resort=resort)

    # If enough past reports, compare runs between reports and create BMReport
    bmreport_runs = []
    if len(past_reports) > 0:
        # Look at each run in today's report
        for run in report.runs.all():
            num_shared_reports = len(list(set(run.reports.all()).intersection(past_reports)))
            ratio = float(num_shared_reports) / float(len(past_reports))

            logger.info('Run {} groomed {:.2%} over the last week'.format(run.name, ratio))
            if ratio < 0.3:
                bmreport_runs.append(run)

    return bmreport_runs


@receiver(post_save, sender=Report)
def create_update_bmreport(instance: Report, created: bool, **kwargs) -> None:
    """
    Create or update the corresponding BMReport object when the Report object is updated

    :param sender: Report class sending signal
    :param instance: Report object being saved
    :param created: True if new object being created; False for update
    """
    bmreport_runs = get_bm_runs(instance)
    if created:
        bm_report = BMReport.objects.create(date=instance.date, resort=instance.resort,
                                            full_report=instance)
        bm_report.runs.set(bmreport_runs)
    else:
        bm_report = instance.bm_report
        bm_report.date = instance.date
        bm_report.resort = instance.resort
        bm_report.runs.set(bmreport_runs)
        bm_report.save()


@receiver(m2m_changed, sender=Report.runs.through)
def update_bmreport(instance: Union[Report, Run], action: str, reverse: bool, **kwargs) -> None:
    """
    Update the bmreport runs field if Report field updated

    :param instance: report object being modified
    :param action: type of update on relation
    :param reverse: True if the Report object is being modified; false if the Run object is being modified
    """
    # If the Report object is being modified (i.e. runs added to report)
    # Instance -> Report
    if action == 'post_add' and reverse:
        bmreport_runs = get_bm_runs(instance)
        instance.bm_report.runs.set(bmreport_runs)
    # If the Run object is being modified (i.e. run created and assigned to report)
    # Instance -> Run
    elif action == 'post_add' and not reverse:
        for report in instance.reports.all():
            bmreport_runs = get_bm_runs(report)
            report.bm_report.runs.set(bmreport_runs)


class BMGUser(models.Model):
    """
    Extend the User model to include a few more fields
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bmg_user')
    favorite_runs = models.ManyToManyField(Run, related_name='users_favorited')
    phone = models.CharField("User Phone number", blank=True, null=True, max_length=15)
    resorts = models.ManyToManyField(Resort, related_name='bmg_users')

    PHONE = 'PH'
    EMAIL = 'EM'
    CONTACT_METHOD_CHOICES = [
        (PHONE, 'Phone'),
        (EMAIL, 'EM')
    ]
    contact_method = models.CharField(max_length=2, choices=CONTACT_METHOD_CHOICES, default=EMAIL)


@receiver(post_save, sender=User)
def create_update_bmguser(instance: User, created: bool, **kwargs) -> None:
    """
    Create or update a corresponding BMGUser object when a User is created

    :param instance: actual instance being created
    :param created: True if instance is actually being created
    """
    if created:
        BMGUser.objects.create(user=instance)
    else:
        instance.bmg_user.save()


@receiver(post_save, sender=User)
def create_user_token(instance: User, created: bool, **kwargs) -> None:
    """
    Create a token for a user when it is created

    :param instance: user instance being saved
    :param created: True if instance is actually being saved
    """
    if created:
        Token.objects.create(user=instance)


class Notification(models.Model):
    """
    Model a notification sent to a user
    """
    bm_user = models.ForeignKey(BMGUser, related_name='notifications', on_delete=models.CASCADE)
    bm_report = models.ForeignKey(BMReport, related_name='notifications', on_delete=models.CASCADE)
    sent = models.DateTimeField("Time when the notification was sent", auto_now_add=True)

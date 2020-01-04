import datetime as dt
from typing import List, Union
import os
import logging

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver


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


class HDReport(models.Model):
    """
    Object model for processed Hidden Diamond grooming report
    """
    date = models.DateField("Date of Grooming Report")
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='hd_reports')
    runs = models.ManyToManyField(Run, related_name='hd_reports')
    full_report = models.OneToOneField(Report, on_delete=models.CASCADE, related_name='hd_report')

    def __str__(self) -> str:
        return '{}: {}'.format(self.resort, self.date.strftime('%Y-%m-%d'))


def get_hd_runs(report: Report) -> List[Run]:
    """
    Extract the hidden diamond runs from the current report data, based on past data. Return the runs that were
    groomed today that have been groomed less than 90% of the past 7 days.

    :param report: Report object hd_runs are pulled from
    :return: list of hidden diamond run objects
    """
    # Get logger
    logger = logging.getLogger('grmrpt_site.reports.views')
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

    # Get past reports for the last 7 days
    date = report.date
    resort = report.resort
    past_reports = Report.objects.filter(date__lt=date, date__gt=(date - dt.timedelta(days=8)),
                                         resort=resort)

    # If enough past reports, compare runs between reports and create HDReport
    hdreport_runs = []
    if len(past_reports) > 0:
        # Look at each run in today's report
        for run in report.runs.all():
            num_shared_reports = len(list(set(run.reports.all()).intersection(past_reports)))
            ratio = float(num_shared_reports) / float(len(past_reports))

            logger.info('Run {} groomed {:.2%} over the last week'.format(run.name, ratio))
            if ratio < 0.3:
                hdreport_runs.append(run)

    return hdreport_runs


@receiver(post_save, sender=Report)
def create_update_hdreport(instance: Report, created: bool, **kwargs) -> None:
    """
    Create or update the corresponding HDReport object when the Report object is updated

    :param sender: Report class sending signal
    :param instance: Report object being saved
    :param created: True if new object being created; False for update
    """
    hdreport_runs = get_hd_runs(instance)
    if created:
        hd_report = HDReport.objects.create(date=instance.date, resort=instance.resort,
                                            full_report=instance)
        hd_report.runs.set(hdreport_runs)
    else:
        hd_report = instance.hd_report
        hd_report.date = instance.date
        hd_report.resort = instance.resort
        hd_report.runs.set(hdreport_runs)
        hd_report.save()


@receiver(m2m_changed, sender=Report.runs.through)
def update_hdreport(instance: Union[Report, Run], action: str, reverse: bool, **kwargs) -> None:
    """
    Update the hdreport runs field if Report field updated

    :param instance: report object being modified
    :param action: type of update on relation
    :param reverse: True if the Report object is being modified; false if the Run object is being modified
    """
    # If the Report object is being modified (i.e. runs added to report)
    # Instance -> Report
    if action == 'post_add' and reverse:
        hdreport_runs = get_hd_runs(instance)
        instance.hd_report.runs.set(hdreport_runs)
    # If the Run object is being modified (i.e. run created and assigned to report)
    # Instance -> Run
    elif action == 'post_add' and not reverse:
        for report in instance.reports.all():
            hdreport_runs = get_hd_runs(report)
            report.hd_report.runs.set(hdreport_runs)


class BMGUser(models.Model):
    """
    Extend the User model to include a few more fields
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bmg_user')
    favorite_runs = models.ManyToManyField(Run, related_name='users_favorited')
    last_contacted = models.DateTimeField("Time of last contact with report info", default=dt.datetime(2020, 1, 1))


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

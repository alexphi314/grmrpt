from typing import List, Tuple, Union, Dict
import datetime as dt
import pytz
import logging
import os
from collections import Counter
import json
import traceback

import requests
import boto3
from django.db.models import Count

from grmrptcore.celery import app
from .models import Run, Resort, Report, BMReport, Alert, Notification

# Create logger
logger = logging.getLogger(__name__)

JSON_DIFF = {
    'Easy': Run.GREEN,
    'Snowshoe': Run.SNOWSHOE,
    'LargePark': Run.TERRAIN_PARK,
    'Intermediate': Run.BLUE,
    'Advanced Intermediate': Run.BLUEBLACK,
    'Expert': Run.BLACK,
    'Extreme Terrain': Run.DOUBLE_BLACK,
    'MediumPark': Run.TERRAIN_PARK,
    'Very difficult': Run.BLACK,
    'SmallPark': Run.TERRAIN_PARK
}

MAMMOTH_DIFF = {
    'Easy': Run.GREEN,
    'Expert': Run.DOUBLE_BLACK,
    'Intermediate': Run.BLUE,
    'Very difficult': Run.BLACK,
    'Difficult': Run.BLUEBLACK,
    'MediumPark': Run.TERRAIN_PARK,
    'Easier': Run.GREENBLUE
}

CRYSTAL_DIFF = {
    'Easy': Run.GREEN,
    'Intermediate': Run.BLUE,
    'Difficult': Run.BLACK,
    'Very difficult': Run.BLACK,
    'Expert': Run.DOUBLE_BLACK,
    'Snowshoe': Run.SNOWSHOE,
    'Easier': Run.GREENBLUE
}

JSON_VAIL_DIFF = {
    'Green': Run.GREEN,
    'Blue': Run.BLUE,
    'Black': Run.BLACK,
    'DoubleBlack': Run.DOUBLE_BLACK,
    'TerrainPark': Run.TERRAIN_PARK
}


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs) -> None:
    """
    Define the periodic tasks
    """
    sender.add_periodic_task(600, check_for_reports)
    sender.add_periodic_task(3600, check_for_alerts)


@app.task
def check_for_reports() -> None:
    """
    Run two tasks in sequence, check for new reports then corresponding notifications

    :return:
    """
    logger.info('Check for new grooming reports')
    for resort in Resort.objects.all():
        check_for_report.delay(resort.id)


@app.task
def check_for_report(resort_id: int) -> None:
    """
    Check for updates to grooming reports in the database

    :param resort_id: id of Resort object to update corresponding reports
    """
    resort = Resort.objects.get(id=resort_id)
    try:
        if resort.parse_mode == 'json':
            response = requests.get(resort.report_url)
            if response.status_code != 200:
                raise ValueError('Unable to fetch grooming report: {}'.format(response.text))

            date, groomed_runs = get_grooming_report(resort.parse_mode, response=response.json())
        else:
            response = requests.post(resort.report_url, data={'ResortId': resort.site_id})
            if response.status_code != 200 or not response.json()['IsSuccessful']:
                raise ValueError('Unable to fetch grooming report: {}'.format(response.text))

            date, groomed_runs = get_grooming_report(resort.parse_mode, response=response.json())

        logger.info('Got grooming report for {} on {}'.format(resort, date.strftime('%Y-%m-%d')))
        time = dt.datetime.now(tz=pytz.timezone('US/Mountain'))
        create_report(date, groomed_runs, resort, time)

        if notify_resort(resort):
            post_message(resort)
        elif notify_resort_no_runs(resort):
            post_no_bmrun_message(resort)

    except Exception as error:
        logger.warning('Got error while checking report for {}'.format(resort.name))
        logger.exception(error)


@app.task
def check_for_alerts() -> None:
    """
    Run a scheduled task to check for alerts and send any that are found
    """
    try:
        alert_list = get_resort_alerts()
        post_alert_message(alert_list)

    except Exception as error:
        logger.warning('Got error while checking alerts')
        logger.exception(error)


def get_grooming_report(parse_mode: str, response: dict) -> Tuple[dt.date, List[Tuple[str, str]]]:
    """
    Fetch the grooming report and return groomed runs

    :param parse_mode: type of parsing to apply to grooming report
    :param response: json serialization of url response
    :return: date and list of groomed run names
    """
    if parse_mode == 'json':
        date = dt.datetime.strptime(response['LastUpdate'], '%Y-%m-%dT%H:%M:%S%z').date()
        runs = []
        for area in response['MountainAreas']:
            for trail in area['Trails']:
                if trail['Grooming'] == 'Yes' or trail['Grooming'] == 'Second Shift' or trail['Grooming'] == 'Top':
                    try:
                        # Mammoth Mountain has a unique naming style
                        if response['Name'] == 'Mammoth Mountain':
                            difficulty = MAMMOTH_DIFF[trail['Difficulty']]
                        elif response['Name'] == 'Crystal Mountain' or response['Name'] == 'Solitude':
                            difficulty = CRYSTAL_DIFF[trail['Difficulty']]
                        else:
                            difficulty = JSON_DIFF[trail['Difficulty']]
                    except KeyError:
                        difficulty = None
                        logger.warning('Unable to find matching difficulty string for run {} with difficulty {} at {}'
                                       .format(trail['Name'], trail['Difficulty'], response['Name']))
                    run_tuple = (trail['Name'].strip(), difficulty)
                    runs.append(run_tuple)

    else:
        date = dt.datetime.strptime(response['Date'][:-7], '%Y-%m-%dT%H:%M:%S.%f').date()
        runs = []
        for area in response['GroomingAreas']:
            for trail in area['Runs']:
                if trail['IsGroomed']:
                    try:
                        difficulty = JSON_VAIL_DIFF[trail['Type']]
                    except KeyError:
                        difficulty = None
                        logger.warning('Unable to find matching difficulty string for run {} with difficulty {}'
                                       .format(trail['Name'], trail['Type']))
                    run_tuple = (trail['Name'].strip(), difficulty)
                    runs.append(run_tuple)

    return date, list(set(runs))


def create_report(date: dt.date, groomed_runs: List[Tuple[str, str]], resort: Resort, time: dt.datetime) -> None:
    """
    Create the grooming report if not in api

    :param date: grooming report date
    :param groomed_runs: list of groomed run name and difficulties
    :param resort: Resort to tie this report to
    :param time: current time in MST
    """
    # Get list of reports already in api and don't create a new report if it already exists
    reports = resort.reports.all().filter(date=date)
    if len(reports) > 0:
        assert len(reports) == 1
        logger.info('Report object already present in api for {} on {}'.format(
            resort.name,
            date.strftime('%Y-%m-%d')
        ))
        report = reports[0]
    else:
        report = Report(date=date, resort=resort)
        report.save()

        logger.info('Successfully created report object in api for {} on {}'.format(
            resort.name,
            date.strftime('%Y-%m-%d')
        ))

    # Fetch the previous report for this resort, if it exists
    current_report_run_names = [run[0] for run in groomed_runs]
    past_report_list = resort.reports.all().filter(date=date-dt.timedelta(days=1))
    assert len(past_report_list) <= 1

    try:
        prev_report_runs = [
            run.name for run in past_report_list[0].runs.all()
        ]
    except IndexError:
        prev_report_runs = []

    # Check if the groomed runs from this report match the groomed runs from the previous report
    # todo: update logic here to not be a fixed time but relative to usual report population time
    if Counter(current_report_run_names) == Counter(prev_report_runs) and \
            time.hour < int(os.getenv('NORUNS_NOTIF_HOUR')):
        logger.info('Found list of groomed runs identical to yesterday\'s report. '
                    'Not appending these runs to report'
                    ' object.')
        return
    elif Counter(current_report_run_names) == Counter(prev_report_runs):
        logger.info('Today\'s groomed runs are equivalent to yesterday\'s report. Given the late hour, '
                    'assuming it is accurate and appending to report.')

    if Counter([run.name for run in report.runs.all()]) != Counter(current_report_run_names):
        runs_to_append = []
        for run_tuple in groomed_runs:
            run_objs = Run.objects.filter(resort=resort).filter(name=run_tuple[0])
            if len(run_objs) > 0:
                assert len(run_objs) == 1
                run_obj = run_objs[0]
                if run_obj.difficulty is None or \
                        (run_tuple[1] is not None and run_obj.difficulty != run_tuple[1]):
                    run_obj.difficulty = run_tuple[1]
                    run_obj.save()
            else:
                run_obj = Run(name=run_tuple[0], resort=resort, difficulty=run_tuple[1])
                run_obj.save()

            runs_to_append.append(run_obj)

        report.runs.set(runs_to_append)

        # Log groomed runs
        logger.info('Groomed runs for {}: {}'.format(resort.name, ', '.join([run.name for run in report.runs.all()])))


def get_most_recent_reports(resort: Resort) -> \
        Union[None, Report]:
    """
    Fetch the most recent report for the input resort, as well as yesterday's report

    :param resort: data representation of resort
    :return: most recent report object
    """
    reports = resort.reports.all().annotate(run_count=Count('runs')).filter(run_count__gt=0).order_by('-date')

    if len(reports) == 0:
        return

    return reports[0]


def notify_resort(resort: Resort) -> bool:
    """
    Query the db to find if this resort needs to be notified about a new BM report.

    :return: True if a notification should be sent
    """
    last_report = get_most_recent_reports(resort)

    # Only include reports with bm reports with runs on them
    if last_report is None or last_report.bm_report.runs.count() == 0:
        return False

    # Check if notification sent for this report
    if hasattr(last_report.bm_report, 'notification') and last_report.bm_report.notification.type != 'no_runs':
        return False

    # Delete the no_run notif if it exists
    if hasattr(last_report.bm_report, 'notification') and last_report.bm_report.notification.type == 'no_runs':
        last_report.bm_report.notification.delete()

    return True


def notify_resort_no_runs(resort: Resort) -> bool:
    """
    Determine if a No Run report should be sent for this resort

    :param resort: Resort to query
    :return: True if a notification should be sent
    """
    time = dt.datetime.now(tz=pytz.timezone('US/Mountain'))
    if time.hour >= int(os.getenv('NORUNS_NOTIF_HOUR')):
        last_report = get_most_recent_reports(resort)

        if last_report is None:
            return False

        if not hasattr(last_report.bm_report, 'notification') and last_report.bm_report.runs.count() == 0:
            return True

    return False


def get_resort_alerts() -> List[BMReport]:
    """
    Fetch the list of BMreports that have not sent out a notification

    :return: list of BMReport objs that are missing a notification
    """
    time = dt.datetime.now(tz=pytz.timezone('US/Mountain'))
    alert_list = []
    # Check after no run notifs should have gone out
    notif_time = dt.time(int(os.getenv('NORUNS_NOTIF_HOUR')), int(os.getenv('ALERT_NOTIF_MIN')))
    if time.time() >= notif_time:
        for resort in Resort.objects.all():
            report = get_most_recent_reports(resort)
            if report is None:
                continue

            # Check the most recent BMreport is the same date as the current time
            if report.bm_report.date != time.date():
                # Create an empty report for today
                create_report(time, [], resort, time=time)
                reports = resort.reports.filter(date=time)
                assert len(reports) == 1
                report = reports[0]

            # If notification sent for most recent BMReport, it's good
            if hasattr(report.bm_report, 'notification'):
                continue

            if not hasattr(report.bm_report, 'alert'):
                alert_list.append(report.bm_report)

    return alert_list


def post_message_to_sns(sns, **kwargs) -> Dict[str, str]:
    """
    Post a message to a SNS topic

    :param sns: sns client used to make publish call
    :param kwargs: various input arguments to publish call
    :return: response from SNS
    """
    response = sns.publish(**kwargs)
    logger.info('Posted message with id {} to {}'.format(response['MessageId'], kwargs['TopicArn']))

    return response


def get_topic_subs(topic_arn: str) -> int:
    """
    Get the number of confirmed subscribers to the input SNS topic arn

    :param topic_arn: topic arn identifier
    :return: number of confirmed subs
    """
    sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                       aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))

    topic_attrs = sns.get_topic_attributes(
        TopicArn=topic_arn
    )

    return int(topic_attrs['Attributes']['SubscriptionsConfirmed'])


def post_message(resort: Resort) -> None:
    """
    Post a BMReport to this resort's SNS topic
    """
    sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                       aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
    bmreport = get_most_recent_reports(resort).bm_report

    # Post to SNS topic
    run_names = [run.name for run in bmreport.runs.all()]
    if bmreport.resort.display_url is not None and bmreport.resort.display_url != '':
        report_link = bmreport.resort.display_url
    else:
        report_link = bmreport.resort.report_url

    email_subj = '{} {} Blue Moon Grooming Report'.format(
        bmreport.date.strftime('%Y-%m-%d'),
        bmreport.resort.name,
    )
    phone_msg = '{}\n' \
                '  * {}\n\n' \
                'Other resort reports: {}\n' \
                'Full report: {}'.format(
                    bmreport.date.strftime('%Y-%m-%d'),
                    '\n  * '.join(run_names),
                    os.getenv('REPORT_URL', ''),
                    report_link
                )
    email_msg = 'Good morning!\n\n'\
                'Today\'s Blue Moon Grooming Report for {} contains:\n'\
                '  * {}\n\n'\
                'Reports for other resorts and continually updated report for {}: {}\n'\
                'Full report: {}'.format(
                    bmreport.resort.name,
                    '\n  * '.join(run_names),
                    bmreport.resort.name,
                    os.getenv('REPORT_URL', ''),
                    report_link
                )

    if get_topic_subs(bmreport.resort.sns_arn) == 0:
        logger.info('The topic for {} has zero subs, not sending message'.format(bmreport.resort.name))
        Notification(bm_report=bmreport).save()
        return

    response = post_message_to_sns(sns, TopicArn=bmreport.resort.sns_arn, MessageStructure='json',
                                   Message=json.dumps({'email': email_msg, 'sms': phone_msg,
                                                       'default': email_msg}), Subject=email_subj,
                                   MessageAttributes={'day_of_week': {'DataType': 'String',
                                                                      'StringValue': bmreport.date.strftime('%a')}})

    if 'MessageId' in response.keys():
        # Post notification record
        Notification(bm_report=bmreport).save()
    else:
        logger.warning('Did not receive MessageId in response from SNS: {}'.format(response))


def post_no_bmrun_message(resort: Resort) -> None:
    """
    Post a 'no bm runs' message to the SNS topic for this resort
    """
    sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                       aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
    report = get_most_recent_reports(resort)

    # Post to SNS topic
    if report.resort.display_url is not None and report.resort.display_url != '':
        report_link = report.resort.display_url
    else:
        report_link = report.resort.report_url

    email_subj = '{} {} Blue Moon Grooming Report'.format(
        report.date.strftime('%Y-%m-%d'),
        report.resort.name,
    )
    phone_msg = '{}\n' \
                '\nThere are no blue moon runs today.\n\n' \
                'Other resort reports: {}\n' \
                'Full report: {}'.format(
                    report.date.strftime('%Y-%m-%d'),
                    os.getenv('REPORT_URL', ''),
                    report_link
                )
    email_msg = 'Good morning!\n\n' \
                '{} has no blue moon runs on today\'s report.\n' \
                'Reports for other resorts and continually updated report for {}: {}\n' \
                'Full report: {}'.format(
                    report.resort.name,
                    report.resort.name,
                    os.getenv('REPORT_URL', ''),
                    report_link
                )

    if get_topic_subs(report.resort.sns_arn) == 0:
        logger.info('The topic for {} has zero subs, not sending message'.format(report.resort.name))
        Notification(bm_report=report.bm_report, type='no_runs').save()
        return

    response = post_message_to_sns(sns, TopicArn=report.resort.sns_arn, MessageStructure='json',
                                   Message=json.dumps({'email': email_msg, 'sms': phone_msg,
                                                       'default': email_msg}), Subject=email_subj,
                                   MessageAttributes={'day_of_week': {'DataType': 'String',
                                                                      'StringValue': report.date.strftime('%a')}})

    if 'MessageId' in response.keys():
        # Post notification record
        Notification(bm_report=report.bm_report, type='no_runs').save()
    else:
        logger.warning('Did not receive MessageId in response from SNS: {}'.format(response))


def post_alert_message(alert_list: List[BMReport]) -> None:
    """
    Post an alert to the SNS topics on alert_list

    :param alert_list: list of BMReports with no notifications sent out
    """
    sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                       aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))

    # Post to SNS topic
    for report in alert_list:
        msg = 'No notification sent for BMReport on {} at {}'.format(
            report.date.strftime('%Y-%m-%d'),
            report.resort.name
        )
        response = post_message_to_sns(sns, TopicArn=os.getenv('ALERT_ARN'), Message=msg,
                                       Subject='BMGRM {} Alert'.format(report.resort.name))

        if 'MessageId' in response.keys():
            # Post alert record
            Alert(bm_report=report).save()
        else:
            logger.warning('Did not receive MessageId in response from SNS: {}'.format(response))

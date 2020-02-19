from typing import List, Tuple, Union, Dict
import re
import datetime as dt
from dateutil.parser import parse
import pytz
import logging
import logging.handlers
import os
from copy import deepcopy
from wsgiref.simple_server import make_server
from collections import Counter
import json
import traceback
import subprocess
import time

from tika import parser
import requests
import boto3

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler
LOG_FILE = '/opt/python/log/fetch-app.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1048576, backupCount=5)
handler.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add Formatter to Handler
handler.setFormatter(formatter)

# add Handler to Logger
logger.addHandler(handler)


class APIError(Exception):
    def __init__(self, message) -> None:
        """
        Overload the basic exception behavior. Put out a log message with the warning before crashing

        :param message: error message to include
        """
        logger.warning(message)
        super().__init__(message)


class CommandError(Exception):
    pass


def resolve_response(url: str, headers: Dict[str, str], api_url: str, request_client) -> Dict:
    """
    Execute a GET request from the api of the given relative url and return a Dict object

    :param url: url to fetch - either a relative or absolute url
    :param headers: http request headers
    :param api_url: url for api server
    :param request_client: client used to make HTTP requests
    :return: dict containing response data
    """
    if api_url not in url:
        url = '/'.join([api_url, url])

    response = request_client.get(url, headers=headers)
    if response.status_code != 200:
        raise APIError('Did not receive valid response from api:\n{}'.format(response.text))

    return response.json()


def get_api(relative_url: str, headers: Dict[str, str], api_url: str, request_client=requests) -> Dict:
    """
    Execute a GEt request for a relative url. Perform pagination tasks to ensure all results are returned.

    :param relative_url: relative url from base api url
    :param headers: http request headers
    :param api_url: url for api server
    :param request_client: client used to make HTTP requests
    :return: dict containing response data
    """
    response = resolve_response(relative_url, headers, api_url, request_client)

    if 'results' in response.keys():
        data = response['results']

        while response['next'] is not None:
            response = resolve_response(response['next'], headers, api_url, request_client)
            data += response['results']

        return data

    else:
        return response


def kill_tika_server() -> None:
    """
    End the process hosting the tika server
    """
    with subprocess.Popen(['ps', 'aux'], stdout=subprocess.PIPE) as ps:
        with subprocess.Popen(['grep', '[t]ika'], stdin=ps.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE) \
         as grep:
            grep_out, grep_err = grep.communicate()
            grep_out = str(grep_out)

            if grep_err != b'':
                raise CommandError(grep_err)

            # Get process id
            assert len(grep_out.split('\n')) == 1
            cols = grep_out.split()
            pid = cols[1]

            ps.kill()
            grep.kill()

    # Kill the process
    with subprocess.Popen(['kill', pid], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as kll:
        _, err = kll.communicate()

        if err != b'':
            raise CommandError(err)

        kll.kill()


def get_grooming_report(parse_mode: str, url: str = None,
                        response: requests.Response = None) -> Tuple[Union[None, dt.datetime], List[str]]:
    """
    Fetch the grooming report and return groomed runs

    :param parse_mode: type of parsing to apply to grooming report
    :param url: optional url where the grooming report pdf can be found
    :param response: optional parameter containing fetched report data
    :return: date and list of groomed run names
    """
    if parse_mode == 'tika':
        try:
            parsed = parser.from_file(url)
            content = parsed['content'].strip()
            trial_re = re.compile(r'^\d+\.?\s(?P<name>(?!\d).*\w+.+(?<!")+$)')
            date_re = re.compile(r'\d\d?,\s\d\d\d\d')
        except AttributeError:
            # This occurs when tika server doesn't respond with anything
            # Attempt to restart the server and re-run the function
            logger.info('Attempting to restart tika server, got bad response')
            kill_tika_server()
            time.sleep(1)
            logger.info('Killed tika server, re-running function call')
            return get_grooming_report(parse_mode, url, response)

        runs = []
        date = None
        for line in content.split('\n'):
            if date_re.search(line.strip()):
                date = parse(line.strip()).date()

            if trial_re.search(line.strip()):
                run_name = trial_re.search(line.strip()).group('name').strip()
                # Remove bogus matches -> long sentences
                # Don't append duplicate run names
                if len(run_name) <= 50 and len(run_name.split(' ')) <= 5 and not \
                        any([run == run_name for run in runs]):
                    runs.append(run_name)
    else:
        response = response.json()

        date_options = []
        runs = []
        for area in response['MountainAreas']:
            date_options.append(dt.datetime.strptime(area['LastUpdate'], '%Y-%m-%dT%H:%M:%S%z'))
            for trial in area['Trails']:
                if trial['Grooming'] == 'Yes':
                    runs.append(trial['Name'].strip())

        date = min(date_options).date()

    return date, runs


def create_report(date: dt.datetime, groomed_runs: List[str], resort_id: int,
                  api_url: str, head: Dict[str, str], get_api_wrapper, request_client=requests) -> None:
    """
    Create the grooming report and push if not in api

    :param date: grooming report date
    :param groomed_runs: list of groomed run names
    :param resort_id: resort id this report corresponds to
    :param api_url: url of api server
    :param head: headers to include with HTTP requests
    :param get_api_wrapper: function used to make HTTP GET requests
    :param request_client: class used to make HTTP requests
    """
    resort_url = '/'.join(['resorts', str(resort_id), ''])
    resort_name = get_api_wrapper('resorts/{}/'.format(resort_id))['name'].replace(' ', '%20')

    # Get list of reports already in api and don't create a new report if it already exists
    reports = get_api_wrapper('reports/?resort={}&date={}'.format(
        resort_name,
        date.strftime('%Y-%m-%d')))
    if len(reports) > 0:
        assert len(reports) == 1
        report_id = reports[0]['id']
        logger.info('Report object already present in api')
    else:
        report_dict = {'date': date.strftime('%Y-%m-%d'), 'resort': '/'.join([api_url, resort_url])}
        report_response = request_client.post('/'.join([api_url, 'reports/']), data=report_dict,
                                              headers=head)

        if report_response.status_code == 201:
            logger.info('Successfully created report object in api')
            report_id = report_response.json()['id']
        else:
            raise APIError('Failed to create report object:\n{}'.format(report_response.text))

    # Fetch the report object
    report_url = '/'.join(['reports', str(report_id), ''])
    report_response = get_api_wrapper(report_url)
    report_runs = deepcopy(report_response.get('runs', []))
    # Strip all runs from report_runs that are not in groomed_runs
    report_runs = [run for run in report_runs if get_api_wrapper(run)['name'] in groomed_runs]

    # Fetch the previous report for this resort, if it exists
    past_report_list = get_api_wrapper('reports/?resort={}&date={}'.format(
        resort_name,
        (date-dt.timedelta(days=1)).strftime('%Y-%m-%d')))
    assert len(past_report_list) <= 1

    try:
        prev_report_runs = [
            get_api_wrapper(run)['name'] for run in past_report_list[0]['runs']
        ]
    except IndexError:
        prev_report_runs = []

    # Check if the groomed runs from this report match the groomed runs from the previous report
    if Counter(groomed_runs) == Counter(prev_report_runs):
        logger.info('Found list of groomed runs identical to yesterday\'s report. '
                    'Not appending these runs to report'
                    ' object.')
        return

    # Connect the run objects to the report object, if they are not already linked
    if len(report_runs) < len(groomed_runs):
        for run in groomed_runs:
            # See if run in api
            run_resp = get_api_wrapper('runs/?name={}&resort={}'.format(
                run,
                resort_name
            ))

            # If run exists, check if the run url is attached to the report
            if len(run_resp) > 0:
                assert len(run_resp) == 1
                run_url = '/'.join([api_url, 'runs', str(run_resp[0]['id']), ''])
            # Otherwise, create the run and attach to report from this end
            else:
                run_data = {'name': run, 'resort': '/'.join([api_url, resort_url])}
                update_response = request_client.post('/'.join([api_url, 'runs/']), data=run_data,
                                                      headers=head)

                if update_response.status_code != 201:
                    raise APIError('Failed to create run object:\n{}'.format(update_response.text))
                run_url = '/'.join([api_url, 'runs', str(update_response.json()['id']), ''])

            if run_url not in report_runs:
                report_runs.append(run_url)

    if report_runs != report_response.get('runs', []):
        # Log groomed runs
        logger.info('Groomed runs: {}'.format(', '.join(groomed_runs)))
        report_response['runs'] = report_runs
        update_report_response = request_client.put('/'.join([api_url, report_url]), data=report_response,
                                                    headers=head)

        if update_report_response.status_code == 200:
            logger.info('Successfully tied groomed runs to report')
        else:
            raise APIError('Failed to update report object:\n{}'.format(update_report_response.text))


def get_most_recent_reports(resort: Dict[str, str], get_api_wrapper) -> \
        Union[None, Tuple[Dict[str, str], str, List[Dict[str, str]]]]:
    """
    Fetch the most recent report for the input resort, as well as yesterday's report

    :param resort: data representation of resort
    :param get_api_wrapper: wrapper function used to make GET requests of api
    :return: data dict of most recent BMReport, url to most recent BMReport, and list of runs groomed yesterday
    """
    reports = get_api_wrapper('reports/?resort={}'.format(resort['name'].replace(' ', '%20')))
    # Only include reports with run objects attached
    reports = [report for report in reports if len(report['runs']) > 0]
    report_dates_list = [dt.datetime.strptime(report['date'], '%Y-%m-%d').date() for report in
                         reports]

    if len(report_dates_list) == 0:
        return

    # Store the url to the most recent bmreport for each resort
    most_recent_report = reports[report_dates_list.index(max(report_dates_list))]
    most_recent_report_url = most_recent_report['bm_report']
    bm_report_data = get_api_wrapper(most_recent_report_url)

    # Get the bm report for yesterday, if it exists, and get the run list
    yesterday = max(report_dates_list) - dt.timedelta(days=1)
    yesterday_report = get_api_wrapper('reports/?date={}&resort={}'.format(
        yesterday.strftime('%Y-%m-%d'),
        resort['name']
    ))
    if len(yesterday_report) > 0:
        assert len(yesterday_report) == 1
        yesterday_runs = get_api_wrapper(yesterday_report[0]['bm_report'])['runs']
    else:
        yesterday_runs = []

    return bm_report_data, most_recent_report_url, yesterday_runs


def get_resorts_to_notify(get_api_wrapper, api_url, request_client, headers) -> List[str]:
    """
    Query the API to find the list of resorts that need to be notified about a new BM report.

    :param get_api_wrapper: lambda function that takes relative url for GET request and returns request in JSON
    :param api_url: url to api
    :param request_client: client used to make HTTP requests
    :param headers: authentication headers to use in requests
    :return: list of bm_report urls to notify for
    """
    contact_list = []
    resorts = get_api_wrapper('resorts/')

    for resort in resorts:
        try:
            bm_report_data, most_recent_report_url, yesterday_runs = get_most_recent_reports(resort,
                                                                                             get_api_wrapper)
        except TypeError:
            continue

        # Only include reports with bm reports with runs on them
        if len(bm_report_data['runs']) == 0:
            continue

        # Check if notification sent for this report
        notification_response = get_api_wrapper('notifications/?bm_pk={}'.format(
            bm_report_data['id']
        ))
        assert len(notification_response) <= 1

        if (len(notification_response) == 0 or
                (len(notification_response) == 1 and notification_response[0]['type'] == 'no_runs')) \
                and Counter(bm_report_data['runs']) != Counter(yesterday_runs):
            # No notification posted for this report
            contact_list.append(most_recent_report_url)

            # Delete the no_run notif if it exists
            if len(notification_response) == 1:
                resp = request_client.delete('{}/notifications/{}/'.format(api_url, notification_response[0]['id']),
                                             headers=headers)
                if resp.status_code != 204:
                    raise APIError('Unable to delete notification: {}'.format(resp.text))

        elif Counter(bm_report_data['runs']) == Counter(yesterday_runs):
            logger.info('BM report run list identical to yesterday for {} -- not sending notification'.format(
                resort['name']
            ))

    return contact_list


def get_resorts_no_bmruns(time: dt.datetime, api_wrapper) -> List[str]:
    """
    Get the list of resorts with no bmruns on today's BMReport

    :param time: current time in mtn timezone
    :param api_wrapper: wrapper function used to make GET requests to api
    :return: list of report urls with no bmruns on today's report
    """
    contact_list = []
    if time.hour >= int(os.getenv('NORUNS_NOTIF_HOUR')):
        resorts = api_wrapper('resorts/')

        for resort in resorts:
            try:
                bm_report_data, most_recent_report_url, _ = get_most_recent_reports(resort, api_wrapper)
            except TypeError:
                continue

            # Check if notification sent for this report
            notification_response = api_wrapper('notifications/?bm_pk={}'.format(
                bm_report_data['id']
            ))

            # Append if no notification sent already and no runs on the report
            if len(notification_response) == 0 and len(bm_report_data['runs']) == 0:
                contact_list.append(most_recent_report_url)

    return contact_list


def get_resort_alerts(time: dt.datetime, api_wrapper: get_api, api_url: str,
                      headers: Dict[str, str], client=requests) -> List[str]:
    """
    Fetch the list of BMreports that have not sent out a notification

    :param time: current time in MTN timezone
    :param api_wrapper: wrapper function used to make api GET requests
    :param api_url: url link to api
    :param headers: headers to include with HTTP requests
    :param client: client used to make HTTP requests
    :return: list of BMReport urls that are missing a notification
    """
    alert_list = []
    # Check after no run notifs should have gone out
    notif_time = dt.time(int(os.getenv('NORUNS_NOTIF_HOUR')), int(os.getenv('ALERT_NOTIF_MIN')))
    if time.time() >= notif_time:
        resorts = api_wrapper('resorts/')

        for resort in resorts:
            try:
                bm_report_data, most_recent_report_url, _ = get_most_recent_reports(resort, api_wrapper)
            except TypeError:
                continue

            # Check the most recent BMreport is the same date as the current time
            if bm_report_data['date'] != time.date().strftime('%Y-%m-%d'):
                # Create an empty report for today
                create_report(time, [], resort['id'], api_url, headers, api_wrapper,
                              request_client=client)
                # Get the created report
                reports = api_wrapper('reports/?resort={}&date={}'.format(
                    resort['name'],
                    time.strftime('%Y-%m-%d'))
                )
                assert len(reports) == 1
                bm_report_data = api_wrapper(reports[0]['bm_report'])
                most_recent_report_url = reports[0]['bm_report']

            # If notification sent for most recent BMReport, it's good
            if bm_report_data['notification'] is not None:
                continue

            # Check if alert sent for this report
            alert_response = api_wrapper('alerts/?bm_pk={}'.format(
                bm_report_data['id']
            ))

            if len(alert_response) == 0:
                alert_list.append(most_recent_report_url)

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


def post_messages(contact_list: List[str], headers: Dict[str, str], api_url: str) -> None:
    """
    Post the input messages to the SNS queue

    :param contact_list: list of bm_report urls to notify
    :param headers: http request headers for authentication
    :param api_url: api url link
    """
    sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                       aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))

    # Post to SNS topic
    for report in contact_list:
        report_data = requests.get(report, headers=headers).json()
        report_date = dt.datetime.strptime(report_data['date'], '%Y-%m-%d')
        resort_data = requests.get(report_data['resort'], headers=headers).json()

        run_names = [requests.get(run, headers=headers).json()['name'] for run in report_data['runs']]
        if resort_data['display_url'] is not None and resort_data['display_url'] != '':
            report_link = resort_data['display_url']
        else:
            report_link = resort_data['report_url']

        email_subj = '{} {} Blue Moon Grooming Report'.format(
            report_data['date'],
            resort_data['name'],
        )
        phone_msg = '{}\n' \
                    '  * {}\n\n' \
                    'Other resort reports: {}\n' \
                    'Full report: {}'.format(
                        report_data['date'],
                        '\n  * '.join(run_names),
                        os.getenv('REPORT_URL', ''),
                        report_link
                    )
        email_msg = 'Good morning!\n\n'\
                    'Today\'s Blue Moon Grooming Report for {} contains:\n'\
                    '  * {}\n\n'\
                    'Reports for other resorts and continually updated report for {}: {}\n'\
                    'Full report: {}'.format(
                        resort_data['name'],
                        '\n  * '.join(run_names),
                        resort_data['name'],
                        os.getenv('REPORT_URL', ''),
                        report_link
                    )

        response = post_message_to_sns(sns, TopicArn=resort_data['sns_arn'], MessageStructure='json',
                                       Message=json.dumps({'email': email_msg, 'sms': phone_msg,
                                                           'default': email_msg}), Subject=email_subj,
                                       MessageAttributes={'day_of_week': {'DataType': 'String',
                                                                          'StringValue': report_date.strftime('%a')}})

        if response['MessageId']:
            # Post notification record
            notification_data = {'bm_report': report}
            response = requests.post('{}/notifications/'.format(api_url), data=notification_data,
                                     headers=headers)
            if response.status_code != 201:
                raise APIError('Unable to create notification record in api: {}'.format(
                    response.text
                ))


def post_no_bmrun_message(contact_list: List[str], headers: Dict[str, str], api_url: str) -> None:
    """
    Post the input messages to the SQS queue

    :param contact_list: list of resorts with no bmruns on today's report
    :param headers: http request headers for authentication
    :param api_url: api url link
    """
    sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                       aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))

    # Post to SNS topic
    for report in contact_list:
        report_data = requests.get(report, headers=headers).json()
        report_date = dt.datetime.strptime(report_data['date'], '%Y-%m-%d')
        resort_data = requests.get(report_data['resort'], headers=headers).json()

        if resort_data['display_url'] is not None:
            report_link = resort_data['display_url']
        else:
            report_link = resort_data['report_url']

        email_subj = '{} {} Blue Moon Grooming Report'.format(
            report_data['date'],
            resort_data['name'],
        )
        phone_msg = '{}\n' \
                    '\nThere are no blue moon runs today.\n\n' \
                    'Other resort reports: {}\n' \
                    'Full report: {}'.format(
                        report_data['date'],
                        os.getenv('REPORT_URL', ''),
                        report_link
                    )
        email_msg = 'Good morning!\n\n' \
                    '{} has no blue moon runs on today\'s report.\n' \
                    'Reports for other resorts and continually updated report for {}: {}\n' \
                    'Full report: {}'.format(
                        resort_data['name'],
                        resort_data['name'],
                        os.getenv('REPORT_URL', ''),
                        report_link
                    )

        response = post_message_to_sns(sns, TopicArn=resort_data['sns_arn'], MessageStructure='json',
                                       Message=json.dumps({'email': email_msg, 'sms': phone_msg,
                                                           'default': email_msg}), Subject=email_subj,
                                       MessageAttributes={'day_of_week': {'DataType': 'String',
                                                                          'StringValue': report_date.strftime('%a')}})

        if response['MessageId']:
            # Post notification record
            notification_data = {'bm_report': report, 'type': 'no_runs'}
            response = requests.post('{}/notifications/'.format(api_url), data=notification_data,
                                     headers=headers)
            if response.status_code != 201:
                raise APIError('Unable to create notification record in api: {}'.format(
                    response.text
                ))


def post_alert_message(alert_list: List[str], headers: Dict[str, str], api_url: str) -> None:
    """
    Post a message to the dev topic for each alert in alert_list

    :param alert_list: list of BMReports with no notifications sent out
    :param headers: authentication headers to provide with GET requests
    :param api_url: api url address
    """
    sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                       aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))

    # Post to SNS topic
    for report in alert_list:
        report_data = requests.get(report, headers=headers).json()
        resort_data = requests.get(report_data['resort'], headers=headers).json()

        msg = 'No notification sent for BMReport on {} at {}'.format(
            report_data['date'],
            resort_data['name']
        )
        response = post_message_to_sns(sns, TopicArn=os.getenv('ALERT_ARN'), Message=msg,
                                       Subject='BMGRM {} Alert'.format(resort_data['name']))

        if response['MessageId']:
            # Post alert record
            alert_data = {'bm_report': report}
            response = requests.post('{}/alerts/'.format(api_url), data=alert_data, headers=headers)
            if response.status_code != 201:
                raise APIError('Unable to create alert record in api: {}'.format(
                    response.text
                ))


def application(environ, start_response):
    API_URL = os.getenv('API_URL')
    TOKEN = os.getenv('TOKEN')
    get_api_wrapper = lambda x: get_api(x, headers={'Authorization': 'Token {}'.format(TOKEN)},
                                        api_url=API_URL)
    headers = {'Authorization': 'Token {}'.format(TOKEN)}

    path = environ['PATH_INFO']
    method = environ['REQUEST_METHOD']
    if method == 'POST':
        try:
            if path == '/':
                request_body_size = int(environ['CONTENT_LENGTH'])
                request_body = environ['wsgi.input'].read(request_body_size).decode()
                logger.info("Received message: %s" % request_body)
                response = 'Got message'
            elif path == '/grmrpt_schedule':
                logger.info("Received task %s scheduled at %s", environ['HTTP_X_AWS_SQSD_TASKNAME'],
                            environ['HTTP_X_AWS_SQSD_SCHEDULED_AT'])

                # Run scheduled task
                # Get list of resorts from api
                resorts = get_api_wrapper('resorts/')

                # Fetch grooming report for each resort
                for resort_dict in resorts:
                    resort = resort_dict['name']
                    report_url = resort_dict['report_url']
                    parse_mode = resort_dict['parse_mode']

                    if parse_mode == 'json':
                        response = requests.get(report_url)
                        if response.status_code != 200:
                            raise ValueError('Unable to fetch grooming report: {}'.format(response.text))

                        date, groomed_runs = get_grooming_report(parse_mode, response=response)
                    else:
                        date, groomed_runs = get_grooming_report(parse_mode, url=report_url)

                    logger.info('Got grooming report for {} on {}'.format(resort, date.strftime('%Y-%m-%d')))

                    create_report(date, groomed_runs, resort_dict['id'], API_URL, headers, get_api_wrapper)

                response = 'Successfully processed grooming reports for all resorts'

            elif path == '/notif_schedule':
                logger.info("Received task %s scheduled at %s", environ['HTTP_X_AWS_SQSD_TASKNAME'],
                            environ['HTTP_X_AWS_SQSD_SCHEDULED_AT'])

                resort_list = get_resorts_to_notify(get_api_wrapper, API_URL,
                                                    requests, headers)
                post_messages(resort_list, headers=headers,
                              api_url=API_URL)

                # Check for no bmrun notifications
                time = dt.datetime.now(tz=pytz.timezone('US/Mountain'))
                no_bmruns_list = get_resorts_no_bmruns(time, get_api_wrapper)
                post_no_bmrun_message(no_bmruns_list, headers=headers,
                                      api_url=API_URL)

                response = 'Successfully checked for notification events'

            elif path == '/alert_schedule':
                logger.info("Received task %s scheduled at %s", environ['HTTP_X_AWS_SQSD_TASKNAME'],
                            environ['HTTP_X_AWS_SQSD_SCHEDULED_AT'])
                time = dt.datetime.now(tz=pytz.timezone('US/Mountain'))
                alert_list = get_resort_alerts(time, get_api_wrapper, API_URL, headers)
                post_alert_message(alert_list, headers=headers,
                                   api_url=API_URL)

                response = 'Successfully checked for alerts'

        except APIError:
            logger.warning('Error processing API request')
            logger.warning(traceback.print_exc())
            response = ''

        except Exception:
            logger.warning('Got exception while processing task')
            logger.warning(traceback.print_exc())
            response = ''

    else:
        logger.warning('Received unexpected method to server {}'.format(method))
        response = 'Unexpected method'

    status = '200 OK'
    headers = [('Content-type', 'text/html')]

    start_response(status, headers)
    return [response]


if __name__ == '__main__':
    httpd = make_server('', 8000, application)
    print("Serving on port 8000...")
    httpd.serve_forever()

from typing import List, Tuple, Union, Dict
import re
import datetime as dt
import logging
import logging.handlers
import os
from copy import deepcopy
from wsgiref.simple_server import make_server
from collections import Counter
import json

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


def get_api(relative_url: str, headers: Dict, api_url: str) -> Dict:
    """
    Execute a GET request from the api of the given relative url and return a Dict object

    :param relative_url: relative url from base api url
    :param headers: http request headers
    :param api_url: url for api server
    :return: dict containing response data
    """
    response = requests.get('/'.join([api_url, relative_url]), headers=headers)
    if response.status_code != 200:
        raise APIError('Did not receive valid response from api:\n{}'.format(response.text))

    return response.json()


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
        parsed = parser.from_file(url)
        content = parsed['content'].strip()
        trial_re = re.compile('^\d+\s(?P<name>(?!\d).*\w+.+(?<!")+$)')
        date_re = re.compile('^\w*\s\d*,\s\d*')

        runs = []
        date = None
        for line in content.split('\n'):
            if date_re.search(line.strip()):
                date = dt.datetime.strptime(line.strip(), '%B %d, %Y').date()

            if trial_re.search(line.strip()):
                runs.append(trial_re.search(line.strip()).group('name').strip())
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
                  api_url: str, token: str, requests, get_api) -> None:
    """
    Create the grooming report and push if not in api

    :param date: grooming report date
    :param groomed_runs: list of groomed run names
    :param resort_id: resort id this report corresponds to
    :param api_url: url of api server
    :param token: Token string for fetch user
    :param requests: class used to make HTTP requests
    :param get_api: function used to make HTTP GET requests
    """
    resort_url = '/'.join(['resorts', str(resort_id), ''])
    head = {'Authorization': 'Token {}'.format(token)}
    resort_name = get_api('resorts/{}/'.format(resort_id), head, api_url)['name'].replace(' ', '%20')

    # Get list of reports already in api and don't create a new report if it already exists
    reports = get_api('reports/?resort={}&date={}'.format(
        resort_name,
        date.strftime('%Y-%m-%d')), head, api_url)
    if len(reports) > 0:
        assert len(reports) == 1
        report_id = reports[0]['id']
        logger.info('Report object already present in api')
    else:
        report_dict = {'date': date.strftime('%Y-%m-%d'), 'resort': '/'.join([api_url, resort_url])}
        report_response = requests.post('/'.join([api_url, 'reports/']), data=report_dict,
                                        headers=head)

        if report_response.status_code == 201:
            logger.info('Successfully created report object in api')
            report_id = report_response.json()['id']
        else:
            raise APIError('Failed to create report object:\n{}'.format(report_response.text))

    # Fetch the report object
    report_url = '/'.join(['reports', str(report_id), ''])
    report_response = get_api(report_url, head, api_url)
    report_runs = deepcopy(report_response.get('runs', []))
    # Strip all runs from report_runs that are not in groomed_runs
    report_runs = [run for run in report_runs if requests.get(run, headers=head).json()['name'] in groomed_runs]

    # Fetch the previous report for this resort, if it exists
    past_report_list = get_api('reports/?resort={}&date={}'.format(
        resort_name,
        (date-dt.timedelta(days=1)).strftime('%Y-%m-%d')), head, api_url)
    assert len(past_report_list) <= 1

    try:
        prev_report_runs = [
            requests.get(run, headers=head).json()['name'] for run in past_report_list[0]['runs']
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
            run_resp = get_api('runs/?name={}&resort={}'.format(
                run,
                resort_name
            ), head, api_url)

            # If run exists, check if the run url is attached to the report
            if len(run_resp) > 0:
                assert len(run_resp) == 1
                run_url = '/'.join([api_url, 'runs', str(run_resp[0]['id']), ''])
            # Otherwise, create the run and attach to report from this end
            else:
                run_data = {'name': run, 'resort': '/'.join([api_url, resort_url])}
                update_response = requests.post('/'.join([api_url, 'runs/']), data=run_data,
                                                headers={'Authorization': 'Token {}'.format(token)})

                if update_response.status_code != 201:
                    raise APIError('Failed to create run object:\n{}'.format(update_response.text))
                run_url = '/'.join([api_url, 'runs', str(update_response.json()['id']), ''])

            if run_url not in report_runs:
                report_runs.append(run_url)

    if report_runs != report_response.get('runs', []):
        # Log groomed runs
        logger.info('Groomed runs: {}'.format(', '.join(groomed_runs)))
        report_response['runs'] = report_runs
        update_report_response = requests.put('/'.join([api_url, report_url]), data=report_response,
                                              headers={'Authorization': 'Token {}'.format(token)})

        if update_report_response.status_code == 200:
            logger.info('Successfully tied groomed runs to report')
        else:
            raise APIError('Failed to update report object:\n{}'.format(update_report_response.text))


def get_resorts_to_notify(get_api_wrapper, api_url) -> List[str]:
    """
    Query the API to find the list of resorts that need to be notified about a new BM report.

    :param get_api_wrapper: lambda function that takes relative url for GET request and returns request in JSON
    :param api_url: api url location
    :return: list of bm_report urls to notify for
    """
    contact_list = []
    resorts = get_api_wrapper('resorts/')
    for resort in resorts:
        reports = get_api_wrapper('reports/?resort={}'.format(resort['name'].replace(' ', '%20')))
        # Only include reports with run objects attached
        reports = [report for report in reports if len(report['runs']) > 0]
        # Only include reports with bm reports with runs on them
        reports = [report for report in reports if len(get_api_wrapper(
            report['bm_report'].replace('{}/'.format(api_url), ''))['runs']
                                                       ) > 0]
        report_dates_list = [dt.datetime.strptime(report['date'], '%Y-%m-%d').date() for report in
                             reports]

        if len(report_dates_list) == 0:
            continue

        # Store the url to the most recent bmreport for each resort
        most_recent_report = reports[report_dates_list.index(max(report_dates_list))]
        most_recent_report_url = most_recent_report['bm_report']
        bm_report_data = get_api_wrapper(most_recent_report_url.replace('{}/'.format(api_url), ''))

        # Get the bm report for yesterday, if it exists, and get the run list
        yesterday = max(report_dates_list) - dt.timedelta(days=1)
        yesterday_report = get_api_wrapper('reports/?date={}&resort={}'.format(
            yesterday.strftime('%Y-%m-%d'),
            resort['name']
        ))
        if len(yesterday_report) > 0:
            assert len(yesterday_report) == 1
            yesterday_runs = get_api_wrapper(yesterday_report[0]['bm_report'].replace(
                '{}/'.format(api_url), ''
            ))['runs']
        else:
            yesterday_runs = []

        # Check if notification sent for this report
        notification_response = get_api_wrapper('notifications/?bm_pk={}'.format(
            bm_report_data['id']
        ))

        if len(notification_response) == 0 and Counter(bm_report_data['runs']) != Counter(yesterday_runs):
            # No notification posted for this report
            contact_list.append(most_recent_report_url)
        elif Counter(bm_report_data['runs']) == Counter(yesterday_runs):
            logger.info('BM report run list identical to yesterday -- not sending notification')

    return contact_list


def post_messages(contact_list: List[str], headers: Dict[str, str], api_url: str) -> None:
    """
    Post the input messages to the SQS queue

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
        if resort_data['display_url'] is not None:
            report_link = resort_data['display_url']
        else:
            report_link = resort_data['report_url']

        email_subj = '{} {} Blue Moon Grooming Report'.format(
            report_data['date'],
            resort_data['name'],
        )
        phone_msg = '{}\n' \
                    '  * {}\n\n' \
                    'Full report: {}'.format(
                        report_data['date'],
                        '\n  * '.join(run_names),
                        report_link
                    )
        email_msg = 'Good morning!\n\n'\
                    'Today\'s Blue Moon Grooming Report for {} contains:\n'\
                    '  * {}\n\n'\
                    'Full report: {}'.format(
                        resort_data['name'],
                        '\n  * '.join(run_names),
                        report_link
                    )

        response = sns.publish(
            TopicArn=resort_data['sns_arn'],
            MessageStructure='json',
            Message=json.dumps({
                'email': email_msg,
                'sms': phone_msg,
                'default': email_msg
            }),
            Subject=email_subj,
            MessageAttributes={
                'day_of_week': {
                    'DataType': 'String',
                    'StringValue': report_date.strftime('%a')
                }
            }
        )
        logger.info('Posted message with id {} to {}'.format(response['MessageId'], resort_data['sns_arn']))

        if response['MessageId']:
            # Post notification record
            notification_data = {'bm_report': report}
            response = requests.post('{}/notifications/'.format(api_url), data=notification_data,
                                     headers=headers)
            if response.status_code != 201:
                raise APIError('Unable to create notification record in api: {}'.format(
                    response.text
                ))


def application(environ, start_response):
    API_URL = os.getenv('DEV_URL')
    TOKEN = os.getenv('DEV_TOKEN')
    get_api_wrapper = lambda x: get_api(x, headers={'Authorization': 'Token {}'.format(TOKEN)},
                                        api_url=API_URL)

    path = environ['PATH_INFO']
    method = environ['REQUEST_METHOD']
    if method == 'POST':
        try:
            if path == '/':
                request_body_size = int(environ['CONTENT_LENGTH'])
                request_body = environ['wsgi.input'].read(request_body_size).decode()
                logger.info("Received message: %s" % request_body)
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

                    create_report(date, groomed_runs, resort_dict['id'], API_URL, TOKEN, requests, get_api)

                response = 'Successfully processed grooming reports for all resorts'

            elif path == '/notif_schedule':
                logger.info("Received task %s scheduled at %s", environ['HTTP_X_AWS_SQSD_TASKNAME'],
                            environ['HTTP_X_AWS_SQSD_SCHEDULED_AT'])

                resort_list = get_resorts_to_notify(get_api_wrapper, API_URL)
                post_messages(resort_list, headers={'Authorization': 'Token {}'.format(TOKEN)},
                              api_url=API_URL)

                response = 'Successfully checked for notification events'

        except (TypeError, ValueError):
            logger.warning('Error retrieving request body for async work.')
            response = ''
        except APIError as e:
            logger.warning('Error processing API request')
            logger.warning(e)
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

from typing import List, Tuple, Union, Dict
import re
import datetime as dt
import logging
import logging.handlers
import os
from copy import deepcopy
from wsgiref.simple_server import make_server

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


def get_api(relative_url: str, headers: Dict, API_URL: str) -> Dict:
    """
    Execute a GET request from the api of the given relative url and return a Dict object

    :param relative_url: relative url from base api url
    :param headers: http request headers
    :param API_URL: url for api server
    :return: dict containing response data
    """
    response = requests.get('/'.join([API_URL, relative_url]), headers=headers)
    if response.status_code != 200:
        raise APIError('Did not receive valid response from api:\n{}'.format(response.text))

    return response.json()


def get_grooming_report(url: str) -> Tuple[Union[None, dt.datetime], List[str]]:
    """
    Fetch the grooming report and return groomed runs

    :param url: url where the grooming report pdf can be found
    :return: date and list of groomed run names
    """
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

    return date, runs


def create_report(date: dt.datetime, groomed_runs: List[str], resort_id: int,
                  API_URL: str, TOKEN: str) -> None:
    """
    Create the grooming report and push if not in api

    :param date: grooming report date
    :param groomed_runs: list of groomed run names
    :param resort_id: resort id this report corresponds to
    :param API_URL: url of api server
    :param TOKEN: Token string for fetch user
    """
    resort_url = '/'.join(['resorts', str(resort_id), ''])
    head = {'Authorization': 'Token {}'.format(TOKEN)}
    resort_name = get_api('resorts/{}'.format(resort_id), head, API_URL)['name'].replace(' ', '%20')

    # Get list of reports already in api and don't create a new report if it already exists
    reports = get_api('reports?resort={}&date={}'.format(
        resort_name,
        date.strftime('%Y-%m-%d')), head, API_URL)
    if len(reports) > 0:
        assert len(reports) == 1
        report_id = reports[0]['id']
        logger.info('Report object already present in api, exiting')
    else:
        report_dict = {'date': date.strftime('%Y-%m-%d'), 'resort': '/'.join([API_URL, resort_url])}
        report_response = requests.post('/'.join([API_URL, 'reports/']), data=report_dict,
                                        headers=head)

        if report_response.status_code == 201:
            logger.info('Successfully created report object in api')
            report_id = report_response.json()['id']
        else:
            raise APIError('Failed to create report object:\n{}'.format(report_response.text))

    # Fetch the report object
    report_url = '/'.join(['reports', str(report_id), ''])
    report_response = get_api(report_url, head, API_URL)
    report_runs = deepcopy(report_response.get('runs', []))

    # Connect the run objects to the report object, if they are not already linked
    if len(report_response['runs']) < len(groomed_runs):
        for run in groomed_runs:
            # See if run in api
            run_resp = get_api('runs?name={}&resort={}'.format(
                run,
                resort_name
            ), head, API_URL)

            # If run exists, check if the run url is attached to the report
            if len(run_resp) > 0:
                assert len(run_resp) == 1
                run_url = '/'.join([API_URL, 'runs', str(run_resp[0]['id']), ''])
            # Otherwise, create the run and attach to report from this end
            else:
                run_data = {'name': run, 'resort': '/'.join([API_URL, resort_url])}
                update_response = requests.post('/'.join([API_URL, 'runs/']), data=run_data,
                                                headers={'Authorization': 'Token {}'.format(TOKEN)})

                if update_response.status_code != 201:
                    raise APIError('Failed to create run object:\n{}'.format(update_response.text))
                run_url = '/'.join([API_URL, 'runs', str(update_response.json()['id']), ''])

            if run_url not in report_runs:
                report_runs.append(run_url)

    if report_runs != report_response.get('runs', []):
        report_response['runs'] = report_runs
        update_report_response = requests.put('/'.join([API_URL, report_url]), data=report_response,
                                              headers={'Authorization': 'Token {}'.format(TOKEN)})

        if update_report_response.status_code == 200:
            logger.info('Successfully tied groomed runs to report')
        else:
            raise APIError('Failed to update report object:\n{}'.format(update_report_response.text))


def get_users_to_notify(get_api_wrapper, api_url) -> List[List[str]]:
    """
    Query the API to find the list of users who need to be notified about a new BM report.

    :param get_api_wrapper: lambda function that takes relative url for GET request and returns request in JSON
    :param api_url: api url location
    :return: list of user urls who need to be notified with the current report
    """
    # Get list of BMGUsers from api
    bmg_users = get_api_wrapper('bmgusers/')

    # Get current report date for each resort
    report_dates = {}
    most_recent_reports = {}
    resorts = get_api_wrapper('resorts/')
    for resort in resorts:
        reports = get_api_wrapper('reports/?resort={}'.format(resort['name'].replace(' ', '%20')))
        report_dates_list = [dt.datetime.strptime(report['date'], '%Y-%m-%d').date() for report in
                                            reports]
        report_dates[resort['name']] = max(report_dates_list)
        # Store the url to the most recent bmreport for each resort
        most_recent_reports[resort['name']] = '{}/bmreports/{}/'.format(
            api_url, reports[report_dates_list.index(max(report_dates_list))]['id']
        )

    # Loop through users
    contact_list = []
    for user in bmg_users:
        try:
            last_contacted_list = user['last_contacted'].split('!')
        except AttributeError:
            last_contacted_list = [None]*len(user['resorts'])

        for last_contacted, resort in zip(last_contacted_list, user['resorts']):
            resort_data = get_api_wrapper(resort)
            if last_contacted is None or \
                    dt.datetime.strptime(last_contacted, '%Y-%m-%d').date() < report_dates[resort_data['name']]:
                contact_list.append(['{}/bmgusers/{}/'.format(api_url, user['id']), resort,
                                     most_recent_reports[resort_data['name']]])

    return contact_list


def application(environ, start_response):
    API_URL = os.getenv('DEV_URL')
    TOKEN = os.getenv('DEV_TOKEN')
    get_api_wrapper = lambda x: get_api(x, headers={'Authorization': 'Token {}'.format(TOKEN)},
                                        API_URL=API_URL)

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

                    date, groomed_runs = get_grooming_report(report_url)
                    logger.info('Got grooming report for {} on {}'.format(resort, date.strftime('%Y-%m-%d')))

                    create_report(date, groomed_runs, resort_dict['id'], API_URL, TOKEN)

                response = 'Successfully processed grooming reports for all resorts'

            elif path == '/users_schedule':
                logger.info("Received task %s scheduled at %s", environ['HTTP_X_AWS_SQSD_TASKNAME'],
                            environ['HTTP_X_AWS_SQSD_SCHEDULED_AT'])

                resort_user_list = get_users_to_notify(get_api_wrapper, API_URL)
                sqs = boto3.client('sqs')

                # Post to SQS Queue
                for user, resort, report in resort_user_list:
                    QUEUE_URL = os.getenv('NOTIFY_WORKER_QUEUE_URL')
                    message_attrs = {
                        'User': {
                            'DataType': 'String',
                            'StringValue': user
                        },
                        'Resort': {
                            'DataType': 'String',
                            'StringValue': resort
                        },
                        'Report': {
                            'DataType': 'String',
                            'StringValue': report
                        }
                    }
                    body = 'Send notification to user {}'.format(user)
                    response = sqs.send_message(
                        QueueUrl=QUEUE_URL,
                        DelaySeconds=10,
                        MessageAttributes=message_attrs,
                        MessageBody=body
                    )
                    logger.info('Posted message {} to SQS user notification queue'.format(response['MessageId']))

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

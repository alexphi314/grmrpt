from typing import List, Tuple, Union, Dict
import re
import datetime as dt
import logging
import os
import sys
import argparse
from copy import deepcopy
from collections import Counter

from tika import parser
import requests


class APIError(Exception):
    def __init__(self, message) -> None:
        """
        Overload the basic exception behavior

        :param message: error message to include
        """
        logger.warning(message)
        super().__init__(message)


def get_api(relative_url: str, headers: Dict) -> Dict:
    """
    Execute a GET request from the api of the given relative url and return a Dict object

    :param relative_url: relative url from base api url
    :param headers: http request headers
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


def create_report(date: dt.datetime, groomed_runs: List[str], resort_id: int) -> None:
    """
    Create the grooming report and push if not in api

    :param date: grooming report date
    :param groomed_runs: list of groomed run names
    :param resort_id: resort id this report corresponds to
    """
    resort_url = '/'.join(['resorts', str(resort_id), ''])
    head = {'Authorization': 'Token {}'.format(TOKEN)}
    resort_name = get_api('resorts/{}'.format(resort_id), head)['name'].replace(' ', '%20')

    # Get list of reports already in api and don't create a new report if it already exists
    reports = get_api('reports?resort={}&date={}'.format(
        resort_name,
        date.strftime('%Y-%m-%d'))
    , head)
    if len(reports) > 0:
        assert len(reports) == 1
        report_id = reports[0]['id']
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
    report_response = get_api(report_url, head)
    report_runs = deepcopy(report_response.get('runs', []))

    # Fetch the previous report for this resort, if it exists
    past_report_list = get_api('reports?resort={}&date={}'.format(
        resort_name,
        (date - dt.timedelta(days=1)).strftime('%Y-%m-%d')), head)
    assert len(past_report_list) <= 1

    try:
        prev_report_runs = [
            requests.get(run, headers=head).json()['name'] for run in past_report_list[0]['runs']
        ]
    except IndexError:
        prev_report_runs = []

    # Check if the groomed runs from this report match the groomed runs from the previous report
    if Counter(groomed_runs) == Counter(prev_report_runs):
        logger.info('Found list of groomed runs identical to yesterday\'s report. Not appending these runs to report'
                    'object.')

    # Connect the run objects to the report object, if they are not already linked
    if len(report_response['runs']) < len(groomed_runs):
        for run in groomed_runs:
            # See if run in api
            run_resp = get_api('runs?name={}&resort={}'.format(
                run,
                resort_name
            ), head)

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


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

    arg_parser = argparse.ArgumentParser(description="Input arguments")
    required = arg_parser.add_argument_group('required arguments')
    environ = required.add_mutually_exclusive_group(required=True)
    environ.add_argument('--local', '-l', action='store_true', help="Fetch data from local api server")
    environ.add_argument('--dev', '-d', action='store_true', help="Fetch data from dev api server")

    args = arg_parser.parse_args()
    if args.local is True:
        API_URL = os.getenv('LOCAL_URL')
        TOKEN = os.getenv('LOCAL_TOKEN')
    else:
        API_URL = os.getenv('DEV_URL')
        TOKEN = os.getenv('DEV_TOKEN')

    logger.info('Running with call: {}'.format(sys.argv[0:]))
    logger.info('Getting list of resorts from api')

    # Get list of resorts from api
    resorts = get_api('resorts/', headers={'Authorization': 'Token {}'.format(TOKEN)})

    # Fetch grooming report for each resort
    for resort_dict in resorts:
        resort = resort_dict['name']
        report_url = resort_dict['report_url']

        date, groomed_runs = get_grooming_report(report_url)
        logger.info('Got grooming report for {} on {}'.format(resort, date.strftime('%Y-%m-%d')))

        create_report(date, groomed_runs, resort_dict['id'])

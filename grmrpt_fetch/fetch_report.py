from typing import List, Tuple, Union, Dict
import re
import datetime as dt
import logging
import os

from tika import parser
import requests

API_URL = 'http://127.0.0.1:8000'


def get_api(relative_url: str) -> Dict:
    """
    Execute a GET request from the api of the given relative url and return a Dict object

    :param relative_url: relative url from base api url
    :return: dict containing response data
    """
    response = requests.get('/'.join([API_URL, '{}'.format(relative_url.replace('/', ''))]))
    if response.status_code != 200:
        raise ValueError('Did not receive valid response from api:\n{}'.format(response.text))

    return response.json()


def get_grooming_report(url: str) -> Tuple[Union[None, dt.datetime], List[str]]:
    """
    Fetch the grooming report and return groomed runs

    :param url: url where the grooming report pdf can be found
    :return: date and list of groomed run names
    """
    parsed = parser.from_file(url)
    content = parsed['content'].strip()
    trial_re = re.compile('^\d+\s(?P<name>(?!\d).*\w+.+$)')
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
    resort_url = '/'.join([API_URL, 'resorts', str(resort_id)])
    # Get list of reports already in api and exit if current report is already in api
    reports = get_api('reports')
    for report in reports:
        if report['resort'] == resort_url and dt.datetime.strptime(report['date'], '%Y-%m-%d') == date:
            logger.info('Report already in api, exiting')
            return

    # Else, create new report
    report_dict = {}
    report_dict['date'] = date.strftime('%Y-%m-%d')
    report_dict['resort'] = resort_url
    response = requests.post('/'.join([API_URL, 'reports/']), data=report_dict)

    if response.status_code == 201:
        logger.info('Successfully created report object in api')
    else:
        logger.info('Failed to create report object:\n{}'.format(response.text))



if __name__ == "__main__":
    logger = logging.getLogger('reports.fetch_report')
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
    logger.info('Getting list of resorts from api')

    # Get list of resorts from api
    resorts = get_api('resorts')

    # Fetch grooming report for each resort
    for resort_dict in resorts:
        resort = resort_dict['name']
        report_url = resort_dict['report_url']

        date, groomed_runs = get_grooming_report(report_url)
        logger.info('Got grooming report for {} on {}'.format(resort, date.strftime('%Y-%m-%d')))

        create_report(date, groomed_runs, resort_dict['id'])

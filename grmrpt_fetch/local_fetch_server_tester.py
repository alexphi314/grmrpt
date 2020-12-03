import logging
import os
import sys
import argparse
import datetime as dt
import pytz

import boto3
import requests

from fetch_server import get_resorts_to_notify, get_api, get_grooming_report, create_report, \
    post_messages, get_resorts_no_bmruns, post_no_bmrun_message, get_resort_alerts, post_alert_message

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))

    arg_parser = argparse.ArgumentParser(description="Input arguments")
    required = arg_parser.add_argument_group('required arguments')
    environ = required.add_mutually_exclusive_group(required=True)
    environ.add_argument('--local', '-l', action='store_true', help="Fetch data from local api server")
    environ.add_argument('--dev', '-d', action='store_true', help="Fetch data from dev api server")
    environ.add_argument('--prod', '-p', action='store_true', help='Fetch data from prod server')

    args = arg_parser.parse_args()
    if args.local is True:
        API_URL = os.getenv('LOCAL_URL')
        TOKEN = os.getenv('LOCAL_TOKEN')
    elif args.dev is True:
        API_URL = os.getenv('DEV_URL')
        TOKEN = os.getenv('DEV_TOKEN')
    else:
        API_URL = os.getenv('PROD_URL')
        TOKEN = os.getenv('PROD_TOKEN')

    logger.info('Running with call: {}'.format(sys.argv[0:]))
    logger.info('Getting list of resorts from api')

    # Get list of resorts from api
    headers = {'Authorization': 'Token {}'.format(TOKEN)}
    resorts = get_api('resorts/', headers=headers, api_url=API_URL)
    time = dt.datetime.now(tz=pytz.timezone('US/Mountain'))
    get_api_wrapper = lambda x: get_api(x, headers=headers,
                                        api_url=API_URL)

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
        elif parse_mode == 'tika':
            date, groomed_runs = get_grooming_report(parse_mode, url=report_url)
        else:
            response = requests.post(report_url, data={'ResortId': resort_dict['site_id']})
            if response.status_code != 200 or not response.json()['IsSuccessful']:
                raise ValueError('Unable to fetch grooming report: {}'.format(response.text))

            date, groomed_runs = get_grooming_report(parse_mode, response=response)

        logger.info('Got grooming report for {} on {}'.format(resort, date.strftime('%Y-%m-%d')))
        create_report(date, groomed_runs, resort_dict['id'], API_URL, {'Authorization': 'Token {}'.format(TOKEN)},
                      get_api_wrapper, time)
    #
    # Check for notif
    resort_list = get_resorts_to_notify(get_api_wrapper, API_URL, headers)
    post_messages(resort_list, headers=headers,
                  api_url=API_URL)

    # Check for no bmrun notifications
    no_bmruns_list = get_resorts_no_bmruns(time, get_api_wrapper)
    post_no_bmrun_message(no_bmruns_list, headers=headers,
                          api_url=API_URL)
    #
    # # Check for alerts
    alert_list = get_resort_alerts(time, get_api_wrapper, headers={'Authorization': 'Token {}'.format(TOKEN)},
                                   api_url=API_URL)
    post_alert_message(alert_list, headers={'Authorization': 'Token {}'.format(TOKEN)},
                       api_url=API_URL)

import logging
import os
import sys
import argparse

import boto3
import requests

from fetch_server import get_resorts_to_notify, get_api, get_grooming_report, create_report, post_messages

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
    resorts = get_api('resorts/', headers={'Authorization': 'Token {}'.format(TOKEN)}, api_url=API_URL)

    # Fetch grooming report for each resort
    for resort_dict in resorts:
        resort = resort_dict['name']
        if resort != 'Steamboat':
            continue
        report_url = resort_dict['report_url']
        parse_mode = resort_dict['parse_mode']

        if parse_mode == 'json':
            response = requests.get(report_url)
            if response.status_code != 200:
                raise ValueError('Unable to fetch grooming report: {}'.format(response.text))

            date, groomed_runs = get_grooming_report(parse_mode, response=response)
        else:
            date, groomed_runs = get_grooming_report(parse_mode, url=report_url)

        create_report(date, groomed_runs, resort_dict['id'], API_URL, TOKEN, requests, get_api)

    # Check for notif
    # get_api_wrapper = lambda x: get_api(x, headers={'Authorization': 'Token {}'.format(TOKEN)},
    #                                     api_url=API_URL)
    # resort_list = get_resorts_to_notify(get_api_wrapper, API_URL)
    # post_messages(resort_list, headers={'Authorization': 'Token {}'.format(TOKEN)}, api_url=API_URL)
    # post_messages(['http://dev-env.exm5cdp7tw.us-west-2.elasticbeanstalk.com/bmreports/29/'],
    #               headers={'Authorization': 'Token {}'.format(TOKEN)}, api_url=API_URL)
    FOO = 1

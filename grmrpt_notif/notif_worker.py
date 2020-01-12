from typing import List, Tuple, Union, Dict
import logging
import logging.handlers
import os
from wsgiref.simple_server import make_server
import json

import requests

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Handler
LOG_FILE = '/opt/python/log/notif-worker.log'
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


def application(environ, start_response):
    API_URL = os.getenv('DEV_URL')
    TOKEN = os.getenv('DEV_TOKEN')
    head = {'Authorization': 'Token {}'.format(TOKEN)}

    path = environ['PATH_INFO']
    method = environ['REQUEST_METHOD']
    if method == 'POST':
        try:
            if path == '/':
                request_body_size = int(environ['CONTENT_LENGTH'])
                request_body = environ['wsgi.input'].read(request_body_size).decode()
                logger.info("Received message: %s" % request_body)

                # Get attributes
                user = environ['X_AWS_SQSD_ATTR_user']
                report = environ['X_AWS_SQSD_ATTR_report']

                # Get user and report data
                user_response = requests.get(user, headers=head)
                if user_response.status_code != 200:
                    raise APIError('Could not fetch user data from api: {}'.format(user_response.text))
                user_data = user_response.json()
                logger.info('Got user data: {}'.format(json.dumps(user_data)))

                report_response = requests.get(report, headers=head)
                if report_response.status_code != 200:
                    raise APIError('Could not fetch report data from api: {}'.format(report_response.text))
                report_data = report_response.json()
                logger.info('Got report data: {}'.format(json.dumps(report_data)))

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

import threading
from typing import List
import os
import logging

import boto3

from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage

logger = logging.getLogger(__name__)


class SESEmailBackend(BaseEmailBackend):
    """
    Overload the Django email sender to use AWS SES
    """
    def __init__(self, *args, **kwargs):
        self._lock = threading.RLock()
        self._ses = boto3.client('ses', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                                 aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
        super().__init__(*args, **kwargs)

    def send_messages(self, email_messages: List[EmailMessage]) -> int:
        """
        Send each email message via AWS SES

        :param email_messages: list of EmailMessage objects to send
        :return: number of email messages sent
        """
        msg_count = 0
        with self._lock:
            for message in email_messages:
                # Send email via SES
                resp = self._ses.send_raw_email(
                    Source=message.from_email,
                    Destinations=message.recipients(),
                    RawMessage={
                        'Data': bytes(message.message())
                    }
                )
                if resp['MessageId']:
                    logger.info('Sent email with id {}'.format(resp['MessageId']))
                    msg_count += 1

        return msg_count

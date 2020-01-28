from django.core.exceptions import ImproperlyConfigured
import requests

from .settings import *


def get_ec2_hostname():
    try:
        ipconfig = 'http://169.254.169.254/latest/meta-data/local-ipv4'
        return requests.get(ipconfig, timeout=10).text
    except Exception:
        error = 'You have to be running on AWS to use AWS settings'
        raise ImproperlyConfigured(error)


ALLOWED_HOSTS.append(get_ec2_hostname())

# Setup HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# SECURE_SSL_REDIRECT = True
# SECURE_HSTS_SECONDS = 60
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

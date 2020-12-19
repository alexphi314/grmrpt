import os

from celery import Celery, signals

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grmrptcore.settings')


@signals.setup_logging.connect
def on_celery_setup_logging(**kwargs):
    pass


app = Celery("grmrptcore")
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

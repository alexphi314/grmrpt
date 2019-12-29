from typing import List, Tuple, Union
import re
import datetime as dt
import logging

from tika import parser
import django
django.setup()

from reports.models import *

#GROOMING_URL = 'https://grooming.lumiplan.pro/beaver-creek-grooming-map.pdf'


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


def create_report(date: dt.datetime, groomed_runs: List[str], resort: Resort) -> None:
    """
    Create the grooming report object and save

    :param date: grooming report date
    :param groomed_runs: list of groomed run names
    :param resort: ski resort this grooming report corresponds to
    """
    rpt = Report.objects.create(date=date, resort=resort)
    rpt.save()

    run_objs = []
    for groomed_run in groomed_runs:
        try:
            run_obj = Run.objects.get(name=groomed_run)
        except Run.DoesNotExist:
            run_obj = Run.objects.create(name=groomed_run, resort=resort)
            run_obj.save()

        run_objs.append(run_obj.pk)

    rpt.run_set.set(run_objs)
    rpt.save()


if __name__ == "__main__":
    # Fetch grooming report for all resorts in the db
    # Store the report in the db
    logger = logging.getLogger('reports.fetch_report')
    for resort in Resort.objects.all():
        date, groomed_runs = get_grooming_report(resort.report_url)
        logger.info('Got grooming report for {} on {}'.format(resort, date.strftime('%Y-%m-%d')))

        if Report.objects.count() == 0 or len(Report.objects.filter(date=date)) == 0:
            create_report(date, groomed_runs, resort)
            logger.info('Saved grooming report to DB')

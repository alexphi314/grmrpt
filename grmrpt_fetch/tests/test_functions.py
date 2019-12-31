import datetime as dt

from django.test import TestCase

from ..fetch_report import get_grooming_report, create_report
from reports.models import *


class ReportFuncTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Beaver Creek', report_url='reports/tests/test_files/dec23.pdf')
        cls.resort.save()

        cls.exp_groomed_runs = ['Cabin Fever', 'Grubstake', 'BC Expressway - Lower', 'BC Expressway - Upper',
                            'Primrose to Strawberry Park', 'Cinch - Lower', 'Dally - Lower', 'Dally - Upper',
                            'Haymeadow', 'Latigo', 'Bridle', 'Stone Creek Meadows', 'Intertwine - Lower',
                            'Intertwine - Upper', 'Middle Primrose', 'Stacker - Lower', 'Centennial - Hohum',
                            'Cinch - Upper', 'Powell', 'Jack Rabbit Alley', 'Sheephorn - Escape',
                            'Centennial - Spruce Face', 'Park 101', 'Sawbuck', 'Redtail', 'Gold Dust',
                            'Piney']

    def test_get_grooming_report(self) -> None:
        """
        Test function properly strips the run names from the file
        """
        date, groomed_runs = get_grooming_report(self.resort.report_url)
        self.assertEqual(date, dt.datetime.strptime('12-23-2019', '%m-%d-%Y').date())


        self.assertListEqual(groomed_runs, self.exp_groomed_runs)

    def test_create_report(self) -> None:
        """
        Test create report generates the correct objects and they are linked properly
        """
        date, groomed_runs = get_grooming_report(self.resort.report_url)
        create_report(date, groomed_runs, self.resort)

        # Check report object correctly generated
        self.assertEqual(len(Report.objects.all()), 1)
        rpt = Report.objects.all()[0]
        self.assertEqual(str(rpt), 'Beaver Creek: 2019-12-23')
        self.assertEqual(rpt.date, dt.datetime.strptime('12-23-2019', '%m-%d-%Y').date())
        self.assertEqual(rpt.resort, self.resort)

        # Check run objects exist and linked
        self.assertEqual(rpt.run_set.count(), len(self.exp_groomed_runs))
        for indx, run in enumerate(rpt.run_set.all()):
            self.assertEqual(self.exp_groomed_runs[indx], run.name)
            self.assertEqual(run.report.all()[0], rpt)
            self.assertEqual(run.resort, self.resort)

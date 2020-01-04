import datetime as dt

from django.test import TestCase

from reports.models import *


class ResortTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Beaver Creek', report_url='reports/tests/test_files/dec23.pdf',
                                           location='Avon, CO')

    def test_str(self) -> None:
        """
        Test __str__ method of model works correctly
        """
        self.assertEqual(str(self.resort), 'Beaver Creek')


class ReportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Beaver Creek', report_url='reports/tests/test_files/dec23.pdf',
                                           location='Avon, CO')
        cls.report = Report.objects.create(date=dt.datetime.strptime('2019-01-09', '%Y-%m-%d'),
                                           resort=cls.resort)

    def test_str(self) -> None:
        """
        Test __str__ method of model works correctly
        """
        self.assertEqual(str(self.report), 'Beaver Creek: 2019-01-09')

    def test_hdreport_update(self) -> None:
        """
        test hdreport object changes accordingly as report object updates
        """
        self.report.date = dt.datetime(2020, 1, 10)
        self.report.resort = Resort.objects.create(name='Vail', report_url='foo', location='Vail')
        self.report.save()

        hd_report = self.report.hd_report
        self.assertEqual(hd_report.date, dt.datetime(2020, 1, 10))
        self.assertEqual(hd_report.resort, self.report.resort)

        # Change resort back to original so other tests dont fail
        self.report.resort = self.resort
        self.report.date = dt.datetime(2019, 1, 9)
        self.report.save()


class HDReportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Beaver Creek', report_url='reports/tests/test_files/dec23.pdf',
                                           location='Avon, CO')
        report = Report.objects.create(date=dt.datetime.strptime('2019-01-09', '%Y-%m-%d'),
                                             resort=cls.resort)
        cls.hdreport = report.hd_report
        run_obj1 = Run.objects.create(name='Cabin Fever', difficulty='green', resort=cls.resort)
        run_obj2 = Run.objects.create(name='Ripsaw', difficulty='black', resort=cls.resort)

        report.runs.set([run_obj1, run_obj2])
        cls.hdreport.runs.set([run_obj2])

    def test_str(self):
        """
        Test __str__ method of model works correctly
        """
        self.assertEqual(str(self.hdreport), 'Beaver Creek: 2019-01-09')


class RunTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Beaver Creek', report_url='reports/tests/test_files/dec23.pdf',
                                           location='Avon, CO')
        cls.report = Report.objects.create(date=dt.datetime.strptime('2019-01-09', '%Y-%m-%d'),
                                           resort=cls.resort)
        cls.run_obj = Run.objects.create(name='Cabin Fever', difficulty='green', resort=cls.resort)
        cls.report.runs.add(cls.run_obj)

    def test_str(self) -> None:
        """
        Test __str__ method of model works correctly
        """
        self.assertEqual(str(self.run_obj), 'Cabin Fever')


class BMGUserTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='foo')

    def test_bmg_user_link(self) -> None:
        self.assertEqual(BMGUser.objects.count(), 1)
        bmg_user = BMGUser.objects.all()[0]
        self.assertEqual(bmg_user.user, self.user)
        self.assertEqual(bmg_user.last_contacted, dt.datetime(2020, 1, 1))
        self.assertEqual(bmg_user.favorite_runs.count(), 0)

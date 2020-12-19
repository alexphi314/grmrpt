import pytz
from collections import Counter
from unittest.mock import patch, call

from freezegun import freeze_time
from django.test import TestCase
from rest_framework.test import APIClient

from reports.tasks import get_grooming_report, notify_resort_no_runs, notify_resort, create_report, get_resort_alerts, \
    check_for_reports, check_for_report, check_for_alerts, get_most_recent_reports, post_message_to_sns, \
    get_topic_subs, post_message, post_no_bmrun_message, post_alert_message
from reports.models import *
from .test_classes import MockTestCase


class ReportFuncTestCase(TestCase):
    def setUp(self) -> None:
        self.exp_groomed_runs4 = [
            ("Buddy's Run", 'blue'), ('Skyline', 'blue'), ('Daybreak', 'blue'), ('See Me', 'black'),
            ('Over Easy', 'blue'), ('Velvet', 'blue'), ('Arc', 'green'), ('Short Cut', 'green'),
            ('Chisholm Trail', 'snowshoe'), ('Drop Out', 'black'), ('Highline', 'blue'),
            ("One O'Clock", 'blue'), ('Right-O-Way', 'green'), ('Bashor', 'blue'), ('Last Chance', 'black'),
            ('High Noon', 'blue'), ('Meadow Lane', 'blue'), ("Huffman's", 'blue'), ('Buckshot', 'blue'),
            ('Flatout', 'green'), ('Ramrod', 'blue'), ('Cowboy Coffee', 'blue'), ('Quickdraw', 'blue'),
            ('Swinger', 'green'), ('Boulevard', 'green'), ("Lil' Rodeo Park", 'park'), ("Maverick's Half Pipe", 'park'),
            ('Concentration Lower', 'blue'), ('Park Lane', 'green'), ('Preview', 'green'), ('Rooster', 'blue'),
            ('Yoo Hoo', 'green'), ('Round About', 'snowshoe'), ('Tower', 'blue'), ('Flying Z Gulch', 'blueblack'),
            ('Between', 'blue'), ('Corridor', 'black'), ('Betwixt', 'blue'), ('Calf Roper', 'blue'),
            ("Jess' Cut-Off", 'blue'), ('Broadway', 'green'), ('Vagabond', 'blue'), ('Spur Run', 'green'),
            ('NASTAR Race Area', 'blue'), ('Duster', 'snowshoe'), ('West Side', 'black'), ('Tomahawk Face', 'blue'),
            ("Ted's Ridge", 'black'), ('Moonlight', 'blue'), ('Lightning', 'blue'), ('So What', 'green'),
            ('Half Hitch', 'blueblack'), ('Beeline', 'green'), ('Tomahawk', 'green'), ('Main Drag', 'blue'),
            ('Valley View', 'black'), ('Headwall North', 'blue'), ('Valley View Lower', 'black'), ('Stampede', 'green'),
            ('Eagles Nest', 'blue'), ('Tornado Lane', 'blue'), ('Rabbit Ears Terrain Park', 'park'),
            ('Why Not', 'green'), ('Chuckwagon', 'black'), ('Longhorn', 'blueblack'), ('Dusk', 'blue'),
            ('Blizzard', 'blue'), ('Ego', 'blue'), ('Flying Z', 'black'), ('Cyclone', 'black'),
            ('Heavenly Daze', 'blue'), ('Vogue', 'blue'), ('Sunset', 'blueblack'), ('Storm Peak Catwalk', 'black'),
            ('Spike', 'blue'), ('Snooze Bar', 'blue'), ("Two O'Clock", 'blueblack'), ('Sunshine Lift Line', 'blue'),
            ('Sundial', 'green'), ('Rough Rider Basin', 'green'), ('Traverse', 'blue'), ('B.C. Ski Way', 'green'),
            ('Flintlock', 'blue'), ('Rendezvous Way', 'green'), ('Rowel', 'blue'), ("Rudi's Run", 'blue'),
            ('Kit', 'blue'), ('Giggle Gulch', 'green'), ('Sitz', 'blue'), ('Sitzback', 'green'),
            ('South Peak Flats', 'green'), ('Storm Peak South', 'black'), ('Rainbow', 'blue'), ('Pup', 'blue')
        ]
        self.report_url4 = 'test_files/sb_jan16.json'

        self.report_url8 = 'test_files/bc_mar3.json'
        self.exp_groomed_runs8 = [
            ('Gold Dust', 'blue'), ('Centennial-Upper', 'green'), ('Solitude', 'green'), ('Stirrup', 'green'),
            ('Gunders', 'blue'), ('Bridle', 'green'), ('Cabin Fever', 'blue'), ('Grubstake', 'blue'),
            ('Leav the Beav', 'green'), ('Intertwine', 'green'), ("President Ford's", 'black'),
            ('Golden Bear', 'blue'), ('Dally', 'green'), ('Roughlock-Upper', 'blue'), ('Booth Gardens', 'green'),
            ('Sheephorn-Upper', 'green'), ('Primrose', 'green'), ('Park 101', 'park'), ('Cinch-Upper', 'green'),
            ('Sawbuck', 'green'), ('Roughlock-Lower', 'green'), ('Red Tail', 'blue'),
            ('Beaver Creek Mountain Expressway', 'green'), ('Zoom Room', 'park'), ('1876', 'blue'),
            ("Centennial-Willy's Face", 'black'), ('Stone Creek Meadows', 'blue'), ('Larkspur-Lower', 'blue'),
            ('Cinch-Lower', 'green'), ('Centennial-Lower', 'blue'), ('Piney', 'green'), ('Red Buffalo', 'green'),
            ('Larkspur Bowl', 'blue'), ('Latigo-Upper', 'blue'), ("President Ford's-Lower", 'blue'),
            ('Powell', 'green'), ('EpicMix Race', 'blue'), ('Little Brave', 'blue'), ('Cookie Crumble', 'green'),
            ('Bitterroot', 'blue'), ('Stacker-Lower', 'blue'), ('Haymeadow', 'green'),
            ('Centennial-Spruce Face', 'black'), ('Latigo-Lower', 'blue')
        ]
        self.report_url8_pdf = 'test_files/bc_mar3.pdf'

    def test_get_grooming_report(self) -> None:
        """
        Test function properly strips the run names from the file
        """
        with open('reports/tests/{}'.format(self.report_url4)) as fin:
            data = json.load(fin)
        date, groomed_runs = get_grooming_report('json', response=data)
        self.assertEqual(date, dt.datetime(2020, 1, 16, tzinfo=pytz.timezone('US/Mountain')).date())
        self.assertEqual(Counter(groomed_runs), Counter(self.exp_groomed_runs4))

        with open('reports/tests/{}'.format(self.report_url8)) as fin:
            data = json.load(fin)
        date, groomed_runs = get_grooming_report('json-vail', response=data)
        self.assertEqual(date, dt.datetime(2020, 3, 3).date())
        self.assertEqual(Counter(groomed_runs), Counter(self.exp_groomed_runs8))


class NotifyNoRunTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create 2 resorts
        cls.resort = Resort.objects.create(name='test1')
        cls.resort2 = Resort.objects.create(name='test2')

        # Create 2 reports
        cls.report = Report.objects.create(date=dt.datetime(2020, 1, 1), resort=cls.resort)
        cls.report2 = Report.objects.create(date=dt.datetime(2020, 1, 2), resort=cls.resort2)

        # Create run
        cls.run1 = Run.objects.create(name='run1', resort=cls.resort)
        cls.run2 = Run.objects.create(name='run2', resort=cls.resort2)
        cls.report.runs.set([cls.run1])
        cls.report2.runs.set([cls.run2])

        cls.user = User.objects.create_user(username='test', password='foo', email='AP_TEST')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')

    def test_norun_notif_list(self) -> None:
        """
        check reports flagged for no_run notification works correctly
        """
        # Check eval before 8 am returns no reports
        with freeze_time('2020-01-03 13:00:00'):
            self.assertFalse(notify_resort_no_runs(self.resort))
            self.assertFalse(notify_resort_no_runs(self.resort2))

        with freeze_time('2020-01-03 16:00:00'):
            # Check eval after 8 am returns both reports
            self.assertTrue(notify_resort_no_runs(self.resort))
            self.assertTrue(notify_resort_no_runs(self.resort2))

            # Add run to BMrpt2 and check it is not returned
            self.report2.bm_report.runs.set([self.run2])
            self.assertTrue(notify_resort_no_runs(self.resort))
            self.assertFalse(notify_resort_no_runs(self.resort2))

            # Remove all runs from the report for resort
            self.report.runs.set([])
            self.assertFalse(notify_resort_no_runs(self.resort))


class NotifyUsersTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create users
        cls.user = User.objects.create_user(username='test', password='foo', email='AP_TEST')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')

        cls.client = APIClient()
        cls.client.credentials(HTTP_AUTHORIZATION='Token ' + cls.token.key)

        # Create report, resort, run objects
        cls.resort_data = {'name': 'Beaver Creek TEST', 'location': 'CO', 'report_url': 'foo',
                           'reports': []}
        resort_response = cls.client.post('/api/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201
        cls.resort_url = 'http://testserver/api/resorts/{}/'.format(resort_response.json()['id'])

        cls.resort_data2 = {'name': 'Vail TEST', 'location': 'CO', 'report_url': 'foo',
                            'reports': []}
        resort_response2 = cls.client.post('/api/resorts/', cls.resort_data2, format='json')
        assert resort_response2.status_code == 201
        cls.resort_url2 = 'http://testserver/api/resorts/{}/'.format(resort_response2.json()['id'])

        cls.run_data1 = {'name': 'Centennial', 'resort': cls.resort_url,
                         'difficulty': 'blue', 'reports': []}
        run_response = cls.client.post('/api/runs/', cls.run_data1, format='json')
        assert run_response.status_code == 201
        cls.run1_url = 'http://testserver/api/runs/{}/'.format(run_response.json()['id'])

        cls.run_data2 = {'name': 'Stone Creek Chutes', 'resort': cls.resort_url,
                         'difficulty': 'black', 'reports': []}
        run_response = cls.client.post('/api/runs/', cls.run_data2, format='json')
        assert run_response.status_code == 201
        cls.run2_url = 'http://testserver/api/runs/{}/'.format(run_response.json()['id'])

        cls.run_data3 = {'name': 'Double Diamond', 'resort': cls.resort_url2,
                         'difficulty': 'black', 'reports': []}
        run_response = cls.client.post('/api/runs/', cls.run_data3, format='json')
        assert run_response.status_code == 201
        cls.run3_url = 'http://testserver/api/runs/{}/'.format(run_response.json()['id'])

        cls.report_data = {'date': '2019-12-31',
                           'resort': cls.resort_url,
                           'runs': [cls.run1_url, cls.run2_url]}
        report_response = cls.client.post('/api/reports/', cls.report_data, format='json')
        assert report_response.status_code == 201

        cls.report_data2 = {'date': '2019-12-31',
                           'resort': cls.resort_url2,
                           'runs': [cls.run3_url]}
        report_response = cls.client.post('/api/reports/', cls.report_data2, format='json')
        assert report_response.status_code == 201
        cls.resort2_report_url = 'http://testserver/api/bmreports/{}/'.format(report_response.json()['id'])
        cls.resort2_id = report_response.json()['id']

        # Create notification
        Notification.objects.create(bm_report=Report.objects.get(pk=1).bm_report)

    def test_func(self) -> None:
        """
        check function returns expected list of reports
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Without BMrun linked to report, no notification sent
        resort1 = Resort.objects.get(pk=1)
        resort2 = Resort.objects.get(pk=2)
        self.assertFalse(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))

        # Link run to bmr
        bmr = BMReport.objects.get(pk=2)
        BMReport.objects.get(pk=1).runs.add(Run.objects.get(pk=1))
        bmr.runs.add(Run.objects.get(pk=1))
        # Since first report has a notification, only second resort should have a notification
        self.assertFalse(notify_resort(resort1))
        self.assertTrue(notify_resort(resort2))

        # Add report on 1-2
        report_data = {'date': '2020-01-02',
                       'resort': self.resort_url,
                       'runs': [self.run1_url, self.run2_url]}
        report_response = client.post('/api/reports/', report_data, format='json')
        assert report_response.status_code == 201
        self.assertFalse(notify_resort(resort1))
        self.assertTrue(notify_resort(resort2))

        # Add run to BMR and check resort is now on notification list
        bmr = BMReport.objects.get(pk=client.get(report_response.json()['bm_report']).json()['id'])
        bmr.runs.add(Run.objects.get(pk=1))
        self.assertTrue(notify_resort(resort1))
        self.assertTrue(notify_resort(resort2))

        # Add report on 1-6
        report_data = {'date': '2020-01-06',
                       'resort': self.resort_url,
                       'runs': [self.run1_url, self.run2_url]}
        report_response = client.post('/api/reports/', report_data, format='json')
        assert report_response.status_code == 201
        resort1_id = report_response.json()['id']
        # Without BMruns on BMReport, no notification
        self.assertFalse(notify_resort(resort1))
        self.assertTrue(notify_resort(resort2))

        bmr = BMReport.objects.get(pk=client.get(report_response.json()['bm_report']).json()['id'])
        bmr.runs.add(Run.objects.get(pk=1))

        # With new report, notify resort2 and updated report
        self.assertTrue(notify_resort(resort1))
        self.assertTrue(notify_resort(resort2))

        # Notify both
        Notification.objects.create(bm_report_id=resort1_id)
        Notification.objects.create(bm_report_id=self.resort2_id)

        # Confirm no notifications to go out
        self.assertFalse(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))

        # Create a bogus report with no runs attached
        report_data = {'date': '2020-01-07',
                       'resort': self.resort_url,
                       'runs': []}
        report_response = client.post('/api/reports/', report_data, format='json')
        assert report_response.status_code == 201
        # Confirm no notifications to go out
        self.assertFalse(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))

        # Create identical bm report and check no notification is readied
        run1 = Run.objects.get(pk=1)
        run2 = Run.objects.get(pk=2)
        bmr = BMReport.objects.get(date=dt.datetime(2020, 1, 7))
        bmr.full_report.runs.set([run1])
        bmr.runs.set([run1])

        rpt = Report.objects.create(date=dt.datetime(2020, 1, 8), resort=Resort.objects.get(pk=1))
        bm2 = rpt.bm_report
        rpt.runs.set([run1])
        bm2.runs.set([run1])

        # Confirm notification goes out even though the previous day's report has the same blue moon runs on it
        self.assertTrue(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))

        bm2.runs.add(run2)
        # Confirm notification ready to go out
        self.assertTrue(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))

        # Send notification
        Notification.objects.create(bm_report_id=bm2.pk)

        # Confirm no notifications to go out
        self.assertFalse(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))

        # Create 2 reports next to each other
        rpt1 = Report.objects.create(date=dt.datetime(2020, 2, 1), resort_id=1)
        rpt1.runs.set([Run.objects.get(id=1)])
        rpt1.bm_report.runs.set([Run.objects.get(id=1)])

        rpt2 = Report.objects.create(date=dt.datetime(2020, 2, 2), resort_id=1)
        rpt2.runs.set([Run.objects.get(id=1)])

        # Confirm no notification goes out because BMreport has no runs
        self.assertFalse(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))

        # Add run to BMreport
        rpt2.bm_report.runs.set([Run.objects.get(id=2)])
        self.assertTrue(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))

        # Post notification for 'no run' and confirm resort still queued for notification
        notif = Notification.objects.create(bm_report_id=rpt2.bm_report.id, type='no_runs')
        self.assertTrue(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))
        self.assertRaises(Notification.DoesNotExist, Notification.objects.get, id=notif.id)

        # add more recent report and confirm it is queued for notification
        rpt = Report.objects.create(date=dt.datetime(2020, 2, 3), resort_id=1)
        rpt.runs.add(Run.objects.get(id=1))
        rpt.bm_report.runs.add(Run.objects.get(id=1))
        self.assertTrue(notify_resort(resort1))
        self.assertFalse(notify_resort(resort2))

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class FetchCreateReportTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Create users
        cls.user = User.objects.create_user(username='test', password='foo', email='AP_TEST')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')

        # Create report, resort, etc
        cls.resort = Resort.objects.create(name='BC TEST', location='CO', report_url='foo')
        cls.report = Report.objects.create(date=dt.datetime(2020, 1, 1).date(), resort=cls.resort)
        cls.run1 = Run.objects.create(name='Ripsaw', resort=cls.resort, difficulty='blue')
        cls.run2 = Run.objects.create(name='Centennial', resort=cls.resort, difficulty='blue')
        cls.run3 = Run.objects.create(name='Larkspur', resort=cls.resort, difficulty='blue')

        cls.time = dt.datetime(2020, 1, 1, 7)

    def test_create_report(self) -> None:
        """
        test report populated with groomed runs
        """
        date = dt.datetime(2020, 1, 1)
        create_report(date.date(), [('Ripsaw', 'blue'), ('Centennial', 'blue')], Resort.objects.get(id=1), self.time)
        self.assertListEqual([self.run1, self.run2], list(self.report.runs.all()))
        self.assertEqual('blue', self.run1.difficulty)
        self.assertEqual('blue', self.run2.difficulty)

    def test_update_report(self) -> None:
        date = dt.datetime(2020, 1, 1)
        # Update report with run1 and run2
        self.report.runs.set([self.run1, self.run2])
        # Set run1 and run2 difficulty to None and assert correctly updated
        self.run1.difficulty = None
        self.run2.difficulty = None
        self.run1.save()
        self.run2.save()

        create_report(date.date(), [('Ripsaw', 'blue'), ('Larkspur', 'blue')], Resort.objects.get(id=1), self.time)
        self.assertListEqual([self.run1, self.run3], list(self.report.runs.all()))
        self.assertEqual('blue', Run.objects.get(id=1).difficulty)
        self.assertEqual('blue', Run.objects.get(id=3).difficulty)

        # Update report with no runs
        self.report.runs.set([])
        create_report(date.date(), [('Ripsaw', 'black'), ('Larkspur', 'green')], Resort.objects.get(id=1), self.time)
        self.assertListEqual([self.run1, self.run3], list(self.report.runs.all()))
        # Confirm difficulty of run1 and run3 updated
        self.assertEqual('black', Run.objects.get(id=1).difficulty)
        self.assertEqual('green', Run.objects.get(id=3).difficulty)

        # Updates report with None difficulty
        self.report.runs.set([])
        create_report(date.date(), [('newrun', None)], Resort.objects.get(id=1), self.time)
        self.assertListEqual([Run.objects.get(id=4)], list(self.report.runs.all()))
        self.assertEqual('newrun', Run.objects.get(id=4).name)
        self.assertEqual(Resort.objects.get(id=1), Run.objects.get(id=4).resort)
        self.assertIsNone(Run.objects.get(id=4).difficulty)

        # Creates new run with blue difficulty
        self.report.runs.set([])
        create_report(date.date(), [('newrun', None), ('newrun2', 'blue')], Resort.objects.get(id=1), self.time)
        self.assertListEqual([Run.objects.get(id=4), Run.objects.get(id=5)], list(self.report.runs.all()))
        self.assertEqual('newrun2', Run.objects.get(id=5).name)
        self.assertEqual(Resort.objects.get(id=1), Run.objects.get(id=5).resort)
        self.assertEqual('blue', Run.objects.get(id=5).difficulty)

    def test_create_report_duplicate_runs(self) -> None:
        """
        Check behavior with duplicate runs groomed two days in a row. Do not create report before 8 am.
        """
        rpt = Report.objects.create(date=dt.datetime(2020, 1, 2).date(), resort=self.resort)
        rpt.runs.set([self.run1, self.run2])

        res = Resort.objects.get(id=1)
        create_report(dt.datetime(2020, 1, 3).date(), [(self.run1.name, 'blue'), (self.run2.name, 'blue')],
                      res, dt.datetime(2020, 1, 3, 7))
        rpt = Report.objects.get(date=dt.datetime(2020, 1, 3).date())
        self.assertListEqual(list(rpt.runs.all()), [])

        # Repeat call with time =8
        create_report(dt.datetime(2020, 1, 3).date(), [(self.run1.name, 'blue'), (self.run2.name, 'blue')],
                      res, dt.datetime(2020, 1, 3, 8))
        rpt = Report.objects.get(date=dt.datetime(2020, 1, 3).date())
        self.assertListEqual(list(rpt.runs.all()), [self.run1, self.run2])

        # Check report creates successfully if groomed runs list is different
        create_report(dt.datetime(2020, 1, 4).date(), [(self.run1.name, 'blue'), (self.run3.name, 'blue')],
                      res, dt.datetime(2020, 1, 4, 7))
        rpt = Report.objects.get(date=dt.datetime(2020, 1, 4).date())
        self.assertListEqual(list(rpt.runs.all()), [self.run1, self.run3])

        create_report(dt.datetime(2020, 1, 5).date(), [(self.run1.name, 'blue')],
                      res, dt.datetime(2020, 1, 5, 8))
        rpt = Report.objects.get(date=dt.datetime(2020, 1, 5).date())
        self.assertListEqual(list(rpt.runs.all()), [self.run1])

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class CheckAlertTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = User.objects.create_user(username='test', password='foo', email='AP_TEST')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')

        cls.resort = Resort.objects.create(name='test1')
        cls.resort.save()
        cls.resort2 = Resort.objects.create(name='test2')
        cls.resort2.save()

        cls.report = Report.objects.create(date=dt.datetime(2020, 2, 2), resort=cls.resort)
        cls.report.save()
        cls.report2 = Report.objects.create(date=dt.datetime(2020, 2, 2), resort=cls.resort2)
        cls.report2.save()

        cls.run1 = Run.objects.create(name='foo', resort=cls.resort)
        cls.run1.save()
        cls.run2 = Run.objects.create(name='foobar', resort=cls.resort2)
        cls.run2.save()

        cls.report.runs.add(cls.run1)
        cls.report2.runs.add(cls.run2)

        # Create 1 notification
        Notification.objects.create(bm_report=cls.report2.bm_report).save()

    def test_get_list(self) -> None:
        """
        test get_list behaves as expected
        """
        with freeze_time('2020-02-02 14:00:00'):
            alert_list = get_resort_alerts()
        self.assertListEqual(alert_list, [])

        # check returns 1 resort after 815
        with freeze_time('2020-02-02 15:16:00'):
            alert_list = get_resort_alerts()
        self.assertListEqual(alert_list, [BMReport.objects.get(id=1)])

        # Add alert to report1
        Alert.objects.create(bm_report_id=1).save()
        with freeze_time('2020-02-02 16:00:00'):
            alert_list = get_resort_alerts()
        self.assertListEqual(alert_list, [])

        # Create report on 2-3 for resort1 with no notification
        res = Report.objects.create(date=dt.datetime(2020, 2, 3), resort=self.resort)
        res.save()
        res.runs.add(self.run1)

        # Check a new report object is created for a time in the future and an alert is queued
        with freeze_time('2020-02-03 14:00:00'):
            alert_list = get_resort_alerts()
        self.assertListEqual(alert_list, [])
        with freeze_time('2020-02-03 16:00:00'):
            alert_list = get_resort_alerts()
        self.assertListEqual(alert_list, [BMReport.objects.get(id=3), BMReport.objects.get(id=4)])

        rpt = Report.objects.get(id=4)
        self.assertListEqual(list(rpt.runs.all()), [])
        self.assertEqual(rpt.resort, self.resort2)
        self.assertEqual(rpt.date, dt.datetime(2020, 2, 3).date())
        Alert.objects.create(bm_report_id=4).save()

        # Check the most recent report is returned
        Alert.objects.get(id=1).delete()
        with freeze_time('2020-02-03 16:00:00'):
            alert_list = get_resort_alerts()
        self.assertListEqual(alert_list, [res.bm_report])
        self.assertEqual(Report.objects.count(), 4)

        # Remove the runs from res and confirm it is not returned
        res.runs.set([])
        self.report.runs.set([])
        with freeze_time('2020-02-03 16:00:00'):
            alert_list = get_resort_alerts()
        self.assertListEqual(alert_list, [])
        self.assertEqual(Report.objects.count(), 4)

    @patch('reports.tasks.post_alert_message', autospec=True)
    @patch('reports.tasks.get_resort_alerts', autospec=True)
    def test_check_for_alerts(self, mock_alerts, mock_post):
        mock_alerts.return_value = [self.report.bm_report, self.report2.bm_report]

        check_for_alerts()
        mock_post.assert_called_with([self.report.bm_report, self.report2.bm_report])

        # Test exception is caught
        mock_post.reset_mock()
        mock_alerts.side_effect = ValueError('test error')
        check_for_alerts()
        self.assertFalse(mock_post.called)


class CheckReportTest(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.resort = Resort.objects.create(name='test1', report_url='http://someurl.com/test.json', parse_mode='json')
        cls.resort.save()
        cls.resort2 = Resort.objects.create(name='test2', report_url='http://someurl.com/test.json',
                                            parse_mode='json-vail')
        cls.resort2.save()

    @patch('reports.tasks.check_for_report.delay', autospec=True)
    def test_check_for_reports(self, mock_check):
        # Test called check_for_report for each resort
        check_for_reports()
        self.assertListEqual([call(1), call(2)], mock_check.call_args_list)

        # Test doesn't fail with no resorts in DB
        self.resort.delete()
        self.resort2.delete()
        check_for_reports()

        # Replace resorts
        self.resort = Resort.objects.create(name='test1', report_url='http://someurl.com/test.json', parse_mode='json')
        self.resort.save()
        self.resort2 = Resort.objects.create(name='test2', report_url='http://someurl.com/test.json',
                                             parse_mode='json-vail')
        self.resort2.save()

    @patch('reports.tasks.create_report', autospec=True)
    @patch('reports.tasks.get_grooming_report', autospec=True)
    @patch('reports.tasks.post_no_bmrun_message', autospec=True)
    @patch('reports.tasks.post_message', autospec=True)
    @patch('reports.tasks.notify_resort_no_runs', autospec=True)
    @patch('reports.tasks.notify_resort', autospec=True)
    @patch('reports.tasks.requests.post', autospec=True)
    @patch('reports.tasks.requests.get', autospec=True)
    def test_check_for_report(self, mock_get, mock_post, mock_notify, mock_no_run_notify, mock_post_msg,
                              mock_no_run_post, mock_grm_rpt, mock_create):
        class MockResponse:
            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code

            def json(self):
                return self.json_data

        good_data = {'IsSuccessful': True}
        bad_data = {'IsSuccessful': False}

        def mocked_requests_get(*args, **kwargs):
            if args[0] == 'http://someurl.com/test.json':
                return MockResponse(good_data, 200)

            return MockResponse(None, 404)

        def mocked_requests_get_bad(*args, **kwargs):
            if args[0] == 'http://someurl.com/test.json':
                return MockResponse(bad_data, 200)

            return MockResponse(None, 404)

        mock_notify.return_value = False
        mock_no_run_notify.return_value = False
        mock_grm_rpt.return_value = (dt.date(2020, 12, 28), ['run1', 'run2'])
        mock_get.side_effect = mocked_requests_get
        with freeze_time('2020-12-28 16:00:00'):
            check_for_report(self.resort.id)
        mock_grm_rpt.assert_called_with('json', response=good_data)
        mock_create.assert_called_with(dt.date(2020, 12, 28), ['run1', 'run2'], self.resort,
                                       dt.datetime(2020, 12, 28, 9, tzinfo=pytz.timezone('US/Mountain')))
        mock_notify.assert_called_with(self.resort)
        mock_no_run_notify.assert_called_with(self.resort)
        self.assertFalse(mock_post_msg.called)
        self.assertFalse(mock_no_run_post.called)

        # Test bad url raises exception but it is caught
        mock_grm_rpt.reset_mock()
        mock_create.reset_mock()
        mock_notify.reset_mock()
        mock_no_run_notify.reset_mock()
        self.resort.report_url = 'foo'
        self.resort.save()
        check_for_report(self.resort.id)
        self.assertFalse(mock_grm_rpt.called)
        self.assertFalse(mock_create.called)
        self.assertFalse(mock_notify.called)
        self.assertFalse(mock_no_run_notify.called)
        self.assertFalse(mock_post_msg.called)
        self.assertFalse(mock_no_run_post.called)

        # Test resort2
        mock_post.side_effect = mocked_requests_get
        with freeze_time('2020-12-28 16:00:00'):
            check_for_report(self.resort2.id)
            mock_grm_rpt.assert_called_with('json-vail', response=good_data)
            mock_create.assert_called_with(dt.date(2020, 12, 28), ['run1', 'run2'], self.resort2,
                                           dt.datetime(2020, 12, 28, 9, tzinfo=pytz.timezone('US/Mountain')))
            mock_notify.assert_called_with(self.resort2)
            mock_no_run_notify.assert_called_with(self.resort2)
            self.assertFalse(mock_post_msg.called)
            self.assertFalse(mock_no_run_post.called)

        # Bad response raises exception but it is caught
        mock_grm_rpt.reset_mock()
        mock_create.reset_mock()
        mock_notify.reset_mock()
        mock_no_run_notify.reset_mock()
        mock_post.side_effect = mocked_requests_get_bad
        check_for_report(self.resort2.id)
        self.assertFalse(mock_grm_rpt.called)
        self.assertFalse(mock_create.called)
        self.assertFalse(mock_notify.called)
        self.assertFalse(mock_no_run_notify.called)
        self.assertFalse(mock_post_msg.called)
        self.assertFalse(mock_no_run_post.called)

        # Check post_message called correctly
        mock_notify.return_value = True
        mock_post.side_effect = mocked_requests_get
        mock_no_run_notify.reset_mock()
        check_for_report(self.resort2.id)
        mock_post_msg.assert_called_with(self.resort2)
        self.assertFalse(mock_no_run_post.called)
        self.assertFalse(mock_no_run_notify.called)

        # Check post_no_bmrun_message called correctly
        mock_notify.return_value = False
        mock_no_run_notify.return_value = True
        mock_post_msg.reset_mock()
        check_for_report(self.resort2.id)
        mock_no_run_post.assert_called_with(self.resort2)
        self.assertFalse(mock_post_msg.called)


class TaskSupportingFunctions(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.resort = Resort.objects.create(name='test1', display_url='www.displayurl.com',
                                           report_url='www.reporturl.com', sns_arn='mockarn1')
        cls.resort.save()
        cls.resort2 = Resort.objects.create(name='test2')
        cls.resort2.save()

        os.environ['ACCESS_ID'] = 'foo'
        os.environ['SECRET_ACCESS_KEY'] = 'bar'

    def test_get_most_recent_reports(self):
        # Confirm no failure if no reports in database
        report = get_most_recent_reports(self.resort)
        self.assertIsNone(report)

        # Add two reports and confirm none returned since neither report has runs
        report = Report.objects.create(date=dt.datetime(2020, 2, 2), resort=self.resort)
        report.save()
        report2 = Report.objects.create(date=dt.datetime(2020, 2, 3), resort=self.resort)
        report2.save()
        self.assertIsNone(get_most_recent_reports(self.resort))

        # Add runs to the earlier report and confirm it is returned
        run1 = Run.objects.create(name='foo', resort=self.resort)
        run2 = Run.objects.create(name='foobar', resort=self.resort)
        run1.save()
        run2.save()
        report.runs.set([run1, run2])
        self.assertEqual(report, get_most_recent_reports(self.resort))

        # Add a run to the second report and confirm it is returned
        report2.runs.add(run2)
        self.assertEqual(report2, get_most_recent_reports(self.resort))

    @patch('reports.tasks.boto3.client', autospec=True)
    def test_post_to_sns(self, mock_client):
        mock_sns = mock_client.return_value
        mock_sns.publish.return_value = {
            'MessageId': 'string',
            'SequenceNumber': 'string'
        }

        post_message_to_sns(mock_sns, foo=1, bar=2, bas='ooompa', TopicArn='mockarn1')
        mock_sns.publish.assert_called_with(foo=1, bar=2, bas='ooompa', TopicArn='mockarn1')

    @patch('reports.tasks.boto3.client', autospec=True)
    def test_get_topic_subs(self, mock_client):
        mock_sns = mock_client.return_value
        mock_sns.get_topic_attributes.return_value = {
            'Attributes': {
                'SubscriptionsConfirmed': '5'
            }
        }

        subs = get_topic_subs('mockarn1')
        self.assertEqual(5, subs)
        mock_sns.get_topic_attributes.assert_called_with(TopicArn='mockarn1')
        mock_client.assert_called_with('sns', region_name='us-west-2', aws_access_key_id='foo',
                                       aws_secret_access_key='bar')

    @patch('reports.tasks.post_message_to_sns', autospec=True)
    @patch('reports.tasks.get_topic_subs', autospec=True)
    @patch('reports.tasks.boto3.client', autospec=True)
    def test_post_message(self, mock_client, mock_get, mock_post):
        mock_sns = mock_client.return_value
        # Create runs and report
        run1 = Run.objects.create(name='test1', resort=self.resort)
        run2 = Run.objects.create(name='test2', resort=self.resort)
        run1.save()
        run2.save()
        report = Report.objects.create(resort=self.resort, date=dt.date(2020, 12, 28))
        report.save()
        report.runs.set([run1, run2])
        report.bm_report.runs.set([run1, run2])
        self.resort.display_url = 'www.displayurl.com'
        self.resort.save()

        # Test no message posted for a resort with zero subs
        mock_get.return_value = 0
        os.environ['REPORT_URL'] = 'www.bmg.com'
        post_message(self.resort)
        mock_client.assert_called_with('sns', region_name='us-west-2', aws_access_key_id='foo',
                                       aws_secret_access_key='bar')
        self.assertFalse(mock_post.called)
        self.assertTrue(hasattr(report.bm_report, 'notification'))
        self.assertIsNone(report.bm_report.notification.type)

        # Nominal test
        report.bm_report.notification.delete()
        mock_get.return_value = 1
        mock_post.return_value = {
            'MessageId': '1',
            'SequenceNumber': 'string'
        }
        phone_msg = "2020-12-28\n  * test1\n  * test2\n\nOther resort reports: www.bmg.com\nFull report: " \
                    "www.displayurl.com"
        email_msg = "Good morning!\n\nToday's Blue Moon Grooming Report for test1 contains:\n  * test1\n  * test2\n\n" \
                    "Reports for other resorts and continually updated report for test1: www.bmg.com\n" \
                    "Full report: www.displayurl.com"
        post_message(self.resort)
        mock_get.assert_called_with('mockarn1')
        mock_post.assert_called_with(mock_sns, TopicArn='mockarn1', MessageStructure='json',
                                     Message=json.dumps({'email': email_msg, 'sms': phone_msg, 'default': email_msg,
                                                         }), Subject='2020-12-28 test1 Blue Moon Grooming Report',
                                     MessageAttributes={'day_of_week': {'DataType': 'String', 'StringValue': 'Mon'}})
        report = Report.objects.get(id=report.id)
        self.assertTrue(hasattr(report.bm_report, 'notification'))
        self.assertIsNone(report.bm_report.notification.type)

        # Return a bad response from SNS and assert notification not created
        mock_post.return_value = {
            'SequenceNumber': 'string'
        }
        report.bm_report.notification.delete()
        post_message(self.resort)
        report = Report.objects.get(id=report.id)
        self.assertFalse(hasattr(report.bm_report, 'notification'))

        # Remove the display url and confirm report_url is used in the messages
        self.resort.display_url = ''
        self.resort.save()
        mock_post.return_value = {
            'MessageId': '1',
            'SequenceNumber': 'string'
        }
        phone_msg = "2020-12-28\n  * test1\n  * test2\n\nOther resort reports: www.bmg.com\nFull report: " \
                    "www.reporturl.com"
        email_msg = "Good morning!\n\nToday's Blue Moon Grooming Report for test1 contains:\n  * test1\n  * test2\n\n" \
                    "Reports for other resorts and continually updated report for test1: www.bmg.com\n" \
                    "Full report: www.reporturl.com"
        post_message(self.resort)
        mock_post.assert_called_with(mock_sns, TopicArn='mockarn1', MessageStructure='json',
                                     Message=json.dumps({'email': email_msg, 'sms': phone_msg, 'default': email_msg,
                                                         }), Subject='2020-12-28 test1 Blue Moon Grooming Report',
                                     MessageAttributes={'day_of_week': {'DataType': 'String', 'StringValue': 'Mon'}})

        # Remove display url entirely
        self.resort.display_url = None
        self.resort.save()
        report = Report.objects.get(id=report.id)
        report.bm_report.notification.delete()
        mock_post.return_value = {
            'MessageId': '1',
            'SequenceNumber': 'string'
        }
        phone_msg = "2020-12-28\n  * test1\n  * test2\n\nOther resort reports: www.bmg.com\nFull report: " \
                    "www.reporturl.com"
        email_msg = "Good morning!\n\nToday's Blue Moon Grooming Report for test1 contains:\n  * test1\n  * test2\n\n" \
                    "Reports for other resorts and continually updated report for test1: www.bmg.com\n" \
                    "Full report: www.reporturl.com"
        post_message(self.resort)
        mock_post.assert_called_with(mock_sns, TopicArn='mockarn1', MessageStructure='json',
                                     Message=json.dumps({'email': email_msg, 'sms': phone_msg, 'default': email_msg,
                                                         }), Subject='2020-12-28 test1 Blue Moon Grooming Report',
                                     MessageAttributes={'day_of_week': {'DataType': 'String', 'StringValue': 'Mon'}})

        # Clean DB
        run1.delete()
        run2.delete()
        report.delete()

    @patch('reports.tasks.post_message_to_sns', autospec=True)
    @patch('reports.tasks.get_topic_subs', autospec=True)
    @patch('reports.tasks.boto3.client', autospec=True)
    def test_post_no_bmrun_message(self, mock_client, mock_get, mock_post):
        mock_sns = mock_client.return_value
        report = Report.objects.create(resort=self.resort, date=dt.date(2020, 12, 28))
        report.save()
        run1 = Run.objects.create(name='test1', resort=self.resort)
        report.runs.add(run1)
        self.resort.display_url = 'www.displayurl.com'
        self.resort.save()

        # No subs - no post sent
        mock_get.return_value = 0
        os.environ['REPORT_URL'] = 'www.bmg.com'
        post_no_bmrun_message(self.resort)
        mock_client.assert_called_with('sns', region_name='us-west-2', aws_access_key_id='foo',
                                       aws_secret_access_key='bar')
        self.assertFalse(mock_post.called)
        self.assertTrue(hasattr(report.bm_report, 'notification'))
        self.assertEqual('no_runs', report.bm_report.notification.type)

        # Normal post
        mock_get.return_value = 10
        report.bm_report.notification.delete()
        mock_post.return_value = {
            'MessageId': '1',
            'SequenceNumber': 'string'
        }
        phone_msg = "2020-12-28\n\nThere are no blue moon runs today.\n\nOther resort reports: www.bmg.com\n" \
                    "Full report: www.displayurl.com"
        email_msg = "Good morning!\n\ntest1 has no blue moon runs on today's report.\n" \
                    "Reports for other resorts and continually updated report for test1: www.bmg.com\n" \
                    "Full report: www.displayurl.com"
        post_no_bmrun_message(self.resort)
        mock_get.assert_called_with('mockarn1')
        mock_post.assert_called_with(mock_sns, TopicArn='mockarn1', MessageStructure='json',
                                     Message=json.dumps({'email': email_msg, 'sms': phone_msg, 'default': email_msg,
                                                         }), Subject='2020-12-28 test1 Blue Moon Grooming Report',
                                     MessageAttributes={'day_of_week': {'DataType': 'String', 'StringValue': 'Mon'}})
        report = Report.objects.get(id=report.id)
        self.assertTrue(hasattr(report.bm_report, 'notification'))
        self.assertEqual('no_runs', report.bm_report.notification.type)

        # Bad response from SNS
        mock_post.return_value = {
            'SequenceNumber': 'string'
        }
        report.bm_report.notification.delete()
        post_no_bmrun_message(self.resort)
        report = Report.objects.get(id=report.id)
        self.assertFalse(hasattr(report.bm_report, 'notification'))

        # Change displayurl to ''
        self.resort.display_url = ''
        self.resort.save()
        mock_post.return_value = {
            'MessageId': '1',
            'SequenceNumber': 'string'
        }
        phone_msg = "2020-12-28\n\nThere are no blue moon runs today.\n\nOther resort reports: www.bmg.com\n" \
                    "Full report: www.reporturl.com"
        email_msg = "Good morning!\n\ntest1 has no blue moon runs on today's report.\n" \
                    "Reports for other resorts and continually updated report for test1: www.bmg.com\n" \
                    "Full report: www.reporturl.com"
        post_no_bmrun_message(self.resort)
        mock_get.assert_called_with('mockarn1')
        mock_post.assert_called_with(mock_sns, TopicArn='mockarn1', MessageStructure='json',
                                     Message=json.dumps({'email': email_msg, 'sms': phone_msg, 'default': email_msg,
                                                         }), Subject='2020-12-28 test1 Blue Moon Grooming Report',
                                     MessageAttributes={'day_of_week': {'DataType': 'String', 'StringValue': 'Mon'}})
        report = Report.objects.get(id=report.id)
        self.assertTrue(hasattr(report.bm_report, 'notification'))
        self.assertEqual('no_runs', report.bm_report.notification.type)

        # Remove displayurl entirely
        self.resort.display_url = None
        self.resort.save()
        report.bm_report.notification.delete()
        mock_post.return_value = {
            'MessageId': '1',
            'SequenceNumber': 'string'
        }
        phone_msg = "2020-12-28\n\nThere are no blue moon runs today.\n\nOther resort reports: www.bmg.com\n" \
                    "Full report: www.reporturl.com"
        email_msg = "Good morning!\n\ntest1 has no blue moon runs on today's report.\n" \
                    "Reports for other resorts and continually updated report for test1: www.bmg.com\n" \
                    "Full report: www.reporturl.com"
        post_no_bmrun_message(self.resort)
        mock_get.assert_called_with('mockarn1')
        mock_post.assert_called_with(mock_sns, TopicArn='mockarn1', MessageStructure='json',
                                     Message=json.dumps({'email': email_msg, 'sms': phone_msg, 'default': email_msg,
                                                         }), Subject='2020-12-28 test1 Blue Moon Grooming Report',
                                     MessageAttributes={'day_of_week': {'DataType': 'String', 'StringValue': 'Mon'}})
        report = Report.objects.get(id=report.id)
        self.assertTrue(hasattr(report.bm_report, 'notification'))
        self.assertEqual('no_runs', report.bm_report.notification.type)

        # Clean DB
        report.delete()
        run1.delete()

    @patch('reports.tasks.post_message_to_sns', autospec=True)
    @patch('reports.tasks.boto3.client', autospec=True)
    def test_post_alert_message(self, mock_client, mock_post):
        mock_sns = mock_client.return_value
        report = Report.objects.create(resort=self.resort, date=dt.date(2020, 12, 28))
        report.save()
        report2 = Report.objects.create(resort=self.resort2, date=dt.date(2020, 12, 27))
        report2.save()
        os.environ['ALERT_ARN'] = 'alertarn'
        mock_post.return_value = {
            'MessageId': '1',
            'SequenceNumber': 'string'
        }

        # Nominal test
        post_alert_message([report.bm_report, report2.bm_report])
        mock_client.assert_called_with('sns', region_name='us-west-2', aws_access_key_id='foo',
                                       aws_secret_access_key='bar')
        msg = ['No notification sent for BMReport on 2020-12-28 at test1',
               'No notification sent for BMReport on 2020-12-27 at test2']
        self.assertListEqual([call(mock_sns, TopicArn='alertarn', Message=msg[0],
                                   Subject='BMGRM test1 Alert'),
                              call(mock_sns, TopicArn='alertarn', Message=msg[1],
                                   Subject='BMGRM test2 Alert')], mock_post.call_args_list)
        self.assertTrue(hasattr(report.bm_report, 'alert'))
        self.assertTrue(hasattr(report2.bm_report, 'alert'))

        # Bad response test
        mock_post.return_value = {
            'SequenceNumber': 'string'
        }
        report.bm_report.alert.delete()
        report2.bm_report.alert.delete()
        post_alert_message([report.bm_report, report2.bm_report])
        report = Report.objects.get(id=report.id)
        report2 = Report.objects.get(id=report2.id)
        self.assertFalse(hasattr(report.bm_report, 'alert'))
        self.assertFalse(hasattr(report2.bm_report, 'alert'))

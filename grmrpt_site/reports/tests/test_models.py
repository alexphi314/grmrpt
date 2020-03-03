import datetime as dt
import time
import sys

from django.test import TestCase
from botocore.client import ClientError
from rest_framework.test import APIClient

sys.path.append('../grmrpt_fetch')
from reports.models import *
from grmrpt_fetch.fetch_server import get_api, get_resorts_no_bmruns, get_topic_subs


class ResortTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Beaver Creek TEST',
                                           report_url='reports/tests/test_files/dec23.pdf',
                                           location='Avon, CO')

    def test_str(self) -> None:
        """
        Test __str__ method of model works correctly
        """
        self.assertEqual(str(self.resort), 'Beaver Creek TEST')

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class ReportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Beaver Creek TEST',
                                           report_url='reports/tests/test_files/dec23.pdf',
                                           location='Avon, CO')
        cls.report = Report.objects.create(date=dt.datetime.strptime('2019-01-09', '%Y-%m-%d'),
                                           resort=cls.resort)

    def test_str(self) -> None:
        """
        Test __str__ method of model works correctly
        """
        self.assertEqual(str(self.report), 'Beaver Creek TEST: 2019-01-09')

    def test_bmreport_update(self) -> None:
        """
        test bmreport object changes accordingly as report object updates
        """
        self.report.date = dt.datetime(2020, 1, 10)
        self.report.resort = Resort.objects.create(name='Vail TEST', report_url='foo', location='Vail')
        self.report.save()

        bm_report = self.report.bm_report
        self.assertEqual(bm_report.date, dt.datetime(2020, 1, 10))
        self.assertEqual(bm_report.resort, self.report.resort)

        # Change resort back to original so other tests dont fail
        self.report.resort = self.resort
        self.report.date = dt.datetime(2019, 1, 9)
        self.report.save()

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class BMReportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Beaver Creek TEST',
                                           report_url='reports/tests/test_files/dec23.pdf',
                                           location='Avon, CO')
        report = Report.objects.create(date=dt.datetime.strptime('2019-01-09', '%Y-%m-%d'),
                                             resort=cls.resort)
        cls.bmreport = report.bm_report
        run_obj1 = Run.objects.create(name='Cabin Fever', difficulty='green', resort=cls.resort)
        run_obj2 = Run.objects.create(name='Ripsaw', difficulty='black', resort=cls.resort)

        report.runs.set([run_obj1, run_obj2])
        cls.bmreport.runs.set([run_obj2])

    def test_str(self):
        """
        Test __str__ method of model works correctly
        """
        self.assertEqual(str(self.bmreport), 'Beaver Creek TEST: 2019-01-09')

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class RunTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Beaver Creek TEST',
                                           report_url='reports/tests/test_files/dec23.pdf',
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

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class BMGUserTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='foo')

    def test_bmg_user_link(self) -> None:
        self.assertEqual(BMGUser.objects.count(), 1)
        bmg_user = BMGUser.objects.all()[0]
        self.assertEqual(bmg_user.user, self.user)
        self.assertEqual(bmg_user.favorite_runs.count(), 0)

    def test_str(self) -> None:
        self.assertEqual(str(BMGUser.objects.all()[0]), 'foo')

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class NotificationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='Vail TEST', report_url='foo', location='Vail')
        cls.report = Report.objects.create(date=dt.datetime(2019, 1, 2).date(), resort=cls.resort)
        cls.notif = Notification.objects.create(bm_report=cls.report.bm_report)

    def test_str(self) -> None:
        self.assertEqual(str(self.notif), '2019-01-02')

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class SNSTopicSubscriptionTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create 2 resorts
        cls.resort = Resort.objects.create(name='resort1', report_url='foo', location='Vail')
        cls.resort2 = Resort.objects.create(name='resort2', report_url='foo', location='Avon')

        # Create 2 users
        cls.user = User.objects.create(username='foo', email='foo@gmail.com')
        cls.user.bmg_user.contact_method = 'PH'
        cls.user.bmg_user.contact_days = json.dumps(['Tue'])
        cls.user.bmg_user.phone = '18006756833'
        cls.user.bmg_user.save()

        cls.user2 = User.objects.create(username='bar', email='foobar@gmail.com')
        cls.user2.bmg_user.contact_method = 'PH'
        cls.user2.bmg_user.phone = '18001234567'
        cls.user2.save()

    def test_sns_topic_creation(self) -> None:
        """
        Test sns topics created for each resort
        """
        sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                              aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
        for resort in [self.resort, self.resort2]:
            response = sns.get_topic_attributes(TopicArn=resort.sns_arn)
            self.assertEqual(response['Attributes']['TopicArn'], resort.sns_arn)

    def test_sns_subscribed(self) -> None:
        """
        Test user subscription works
        """
        sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                           aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))

        # Link user to resort and resort2
        self.user.bmg_user.resorts.set([self.resort, self.resort2])
        self.user2.bmg_user.resorts.set([self.resort])
        self.user.bmg_user.save()

        # Check topic arns show correct number of subs
        time.sleep(60)
        self.assertEqual(get_topic_subs(self.resort.sns_arn), 2)
        self.assertEqual(get_topic_subs(self.resort2.sns_arn), 1)

        for indx, subscription in enumerate(json.loads(self.user.bmg_user.sub_arn)):
            response = sns.get_subscription_attributes(SubscriptionArn=subscription)
            if indx == 0:
                arn = self.resort.sns_arn
            else:
                arn = self.resort2.sns_arn

            self.assertEqual(response['Attributes']['TopicArn'], arn)

        # Link user to resort3
        resort3 = Resort.objects.create(name='resort3', report_url='foo', location='Vail')
        self.user.bmg_user.resorts.add(resort3)
        self.assertEqual(len(json.loads(self.user.bmg_user.sub_arn)), 3)
        time.sleep(60)
        self.assertEqual(get_topic_subs(resort3.sns_arn), 1)

        # Remove link to resort2
        self.user.bmg_user.resorts.remove(self.resort2)
        self.user2.bmg_user.resorts.remove(self.resort)
        self.assertEqual(len(json.loads(self.user.bmg_user.sub_arn)), 2)

        # Check sub numbers
        time.sleep(60)
        self.assertEqual(get_topic_subs(self.resort.sns_arn), 1)
        self.assertEqual(get_topic_subs(self.resort2.sns_arn), 0)

        for indx, subscription in enumerate(json.loads(self.user.bmg_user.sub_arn)):
            response = sns.get_subscription_attributes(SubscriptionArn=subscription)
            if indx == 0:
                arn = self.resort.sns_arn
            else:
                arn = resort3.sns_arn

            self.assertEqual(response['Attributes']['TopicArn'], arn)

        # Delete resort3
        resort3.delete()

    def test_delete_resort(self) -> None:
        """
        test deleting resort removes sns topic
        """
        resort = Resort.objects.create(name='resort4', report_url='foo', location='Vail')
        arn = resort.sns_arn
        resort.delete()

        sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                           aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
        self.assertRaises(ClientError, sns.get_topic_attributes, TopicArn=arn)

    def test_sns_update_reverse(self) -> None:
        """
        test subscription from reverse side works
        """
        sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                           aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
        # Link user2 to resort2
        self.resort2.bmg_users.add(self.user2.bmg_user)
        self.assertEqual(len(json.loads(self.user2.bmg_user.sub_arn)), 1)
        response = sns.get_subscription_attributes(SubscriptionArn=self.user2.bmg_user.sub_arn[0])
        self.assertEqual(response['Attributes']['TopicArn'], self.resort2.sns_arn)

        response = sns.get_topic_attributes(TopicArn=self.resort2.sns_arn)
        self.assertEqual(response['Attributes']['SubscriptionsConfirmed'], '1')

    def test_user_delete(self) -> None:
        """
        test deleting user removes subscription
        """
        usr3 = User.objects.create(username='bas', email='foobar1@gmail.com')
        usr3.bmg_user.contact_method = 'PH'
        usr3.bmg_user.phone = '13037765456'
        usr3.bmg_user.save()

        # Check user linked to topic and removed when deleted
        sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                           aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
        usr3.bmg_user.resorts.add(self.resort2)
        sub_arn = json.loads(usr3.bmg_user.sub_arn)[0]
        usr3.delete()
        time.sleep(60)
        self.assertRaises(ClientError, sns.get_subscription_attributes, SubscriptionArn=sub_arn)

        # Confirm deleting BMGUser directly also removes sub
        usr3 = User.objects.create(username='basfoo', email='foobar2@gmail.com')
        usr3.bmg_user.contact_method = 'PH'
        usr3.bmg_user.phone = '13037765456'
        usr3.bmg_user.save()
        usr3.bmg_user.resorts.set([self.resort2, self.resort])
        sub_arns = json.loads(usr3.bmg_user.sub_arn)
        usr3.bmg_user.delete()

        time.sleep(60)
        for sub_arn in sub_arns:
            self.assertRaises(ClientError, sns.get_subscription_attributes, SubscriptionArn=sub_arn)

    def test_contact_day_update(self) -> None:
        """
        test updating contact days causes subscription to update attrs
        """
        sns = boto3.client('sns', region_name='us-west-2', aws_access_key_id=os.getenv('ACCESS_ID'),
                           aws_secret_access_key=os.getenv('SECRET_ACCESS_KEY'))
        # Connect user2 to resort1
        self.user2.bmg_user.resorts.add(self.resort)

        # Check filter policy is set on resort sub
        sub_arn = json.loads(self.user2.bmg_user.sub_arn)[0]
        response = sns.get_subscription_attributes(SubscriptionArn=sub_arn)
        self.assertTrue('FilterPolicy' not in response['Attributes'].keys())

        # Add resort2
        self.user2.bmg_user.resorts.add(self.resort2)
        # Update contact days
        self.user2.bmg_user.contact_days = json.dumps(['Tue', 'Wed'])
        self.user2.save()
        # Add resort4
        resort4 = Resort.objects.create(name='resort4', report_url='foo', location='Vail')
        self.user2.bmg_user.resorts.add(resort4)

        # Check filter policy is set correctly
        sub_arns = json.loads(self.user2.bmg_user.sub_arn)
        for sub_arn in sub_arns:
            response = sns.get_subscription_attributes(SubscriptionArn=sub_arn)
            filter_policy = json.loads(response['Attributes']['FilterPolicy'])

            self.assertListEqual(filter_policy['day_of_week'], ['Tue', 'Wed'])

        # Change contact days again
        self.user2.bmg_user.contact_days = json.dumps(['Thu'])
        self.user2.save()

        # Check filter policy is set correctly
        sub_arns = json.loads(self.user2.bmg_user.sub_arn)
        for sub_arn in sub_arns:
            response = sns.get_subscription_attributes(SubscriptionArn=sub_arn)
            filter_policy = json.loads(response['Attributes']['FilterPolicy'])

            self.assertListEqual(filter_policy['day_of_week'], ['Thu'])

        self.user2.bmg_user.resorts.set([])

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        User.objects.all().delete()
        super().tearDownClass()


class NotifyNoRunTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
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
        time = dt.datetime(2020, 1, 3, 7)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        get_api_wrapper = lambda x: get_api(x, {}, 'http://testserver/api', request_client=client)

        # Check eval before 8 am returns no reports
        reports_list = get_resorts_no_bmruns(time, get_api_wrapper)
        self.assertListEqual(reports_list, [])

        time = dt.datetime(2020, 1, 3, 9)
        # Check eval after 8 am returns both reports
        reports_list = get_resorts_no_bmruns(time, get_api_wrapper)
        self.assertListEqual(reports_list, ['http://testserver/api/bmreports/1/',
                                            'http://testserver/api/bmreports/2/'])

        # Add run to BMrpt2 and check it is not returned
        self.report2.bm_report.runs.set([self.run2])
        reports_list = get_resorts_no_bmruns(time, get_api_wrapper)
        self.assertListEqual(reports_list, ['http://testserver/api/bmreports/1/'])


class AlertTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.resort = Resort.objects.create(name='test1')

        cls.report = Report.objects.create(date=dt.datetime(2020, 2, 1), resort=cls.resort)

        cls.alert = Alert.objects.create(bm_report_id=1)

    def test_str_method(self) -> None:
        """
        test string method works as intended on model
        """
        self.assertEqual(self.alert.sent.strftime('%Y-%m-%dT%H:%M:%S'), str(self.alert))


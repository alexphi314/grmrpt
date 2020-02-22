import json

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from reports.models import *


class SignupTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create resort
        cls.resort = Resort.objects.create(name='test1')

    def test_signup(self) -> None:
        # Attempt to signup
        user_data = {
            'username': 'alexphi',
            'first_name': 'alex',
            'last_name': 'bill',
            'email': 'AP_TEST_foo@gmail.com',
            'password1': 'barfoobas',
            'password2': 'barfoobas',
            'phone': '+13038776576',
            'contact_method': 'EM',
            'contact_days': ["Mon"],
            'resorts': ['test1']
        }
        resp = self.client.post(reverse('signup'), data=user_data)
        self.assertEqual(resp.status_code, 302)

        users = User.objects.all()
        self.assertEqual(len(users), 1)
        usr = users[0]

        self.assertEqual(usr.username, 'alexphi')
        self.assertEqual(usr.first_name, 'alex')
        self.assertEqual(usr.last_name, 'bill')
        self.assertEqual(usr.email, 'AP_TEST_foo@gmail.com')
        self.assertEqual(usr.bmg_user.phone, '+13038776576')
        self.assertEqual(usr.bmg_user.contact_method, 'EM')
        self.assertListEqual(json.loads(usr.bmg_user.contact_days.replace('\'', '\"')), ['Mon'])

        user_data['phone'] = '+13038776577'
        user_data['username'] = 'alexphi2'
        user_data['email'] = 'AP_TEST_foo2@gmail.com'
        self.assertEqual(self.client.post(reverse('signup'), data=user_data).status_code, 302)

        # Incorrect phone number causes an error and no redirection
        user_data['phone'] = '4'
        user_data['username'] = 'alexphi3'
        user_data['email'] = 'AP_TEST_foo3@gmail.com'
        self.assertEqual(self.client.post(reverse('signup'), data=user_data).status_code, 200)

        # Incorrect phone number causes an error and no redirection
        user_data['phone'] = '3038776576'
        user_data['username'] = 'alexphi3'
        user_data['email'] = 'AP_TEST_foo4@gmail.com'
        self.assertEqual(self.client.post(reverse('signup'), data=user_data).status_code, 200)

        self.client.force_login(user=usr)
        self.client.get(reverse('profile'))

    def test_signup_required_fields(self) -> None:
        """
        Test that the form fails when resorts is supplied but no contact_days or contact_method.
        """
        user_data = {
            'username': 'alexphi57',
            'first_name': 'alex',
            'last_name': 'bill',
            'email': 'AP_TEST_foo57@gmail.com',
            'password1': 'barfoobas',
            'password2': 'barfoobas',
            'phone': '+18001234567',
            'resorts': []
        }
        resp = self.client.post(reverse('signup'), data=user_data)
        self.assertEqual(resp.status_code, 302)

        # Include resorts causes error
        user_data['resorts'] = ['test1']
        resp = self.client.post(reverse('signup'), data=user_data)
        self.assertEqual(resp.status_code, 200)

        # Include contact_days only causes error
        user_data['contact_days'] = ["Mon"]
        resp = self.client.post(reverse('signup'), data=user_data)
        self.assertEqual(resp.status_code, 200)

        # Include contact_method only causes error
        del user_data['contact_days']
        user_data['contact_method'] = 'EM'
        resp = self.client.post(reverse('signup'), data=user_data)
        self.assertEqual(resp.status_code, 200)

        # Include both contact_days and contact_method works
        user_data['contact_days'] = ["Mon"]
        user_data['username'] = 'alexphi18'
        user_data['phone'] = '+18009876543'
        user_data['email'] = 'AP_TEST18@gmail.com'
        resp = self.client.post(reverse('signup'), data=user_data)
        self.assertEqual(resp.status_code, 302)


class ReportsViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a user
        cls.usr = User.objects.create_user(username='wildbill')

        # Create 2 resorts
        cls.resort = Resort.objects.create(name='test1')
        cls.resort2 = Resort.objects.create(name='test2')

        # Create 2 reports
        cls.report = Report.objects.create(date=dt.datetime(2020, 2, 1), resort_id=1)
        cls.report2 = Report.objects.create(date=dt.datetime(2020, 1, 31), resort_id=2)

        # Create 2 runs
        cls.run1 = Run.objects.create(name='foo', resort_id=1)
        cls.run2 = Run.objects.create(name='bar', resort_id=2)

        # Add runs to BMReport
        cls.report.bm_report.runs.add(cls.run1)
        cls.report2.bm_report.runs.add(cls.run2)

    def test_view(self) -> None:
        client = Client()
        client.force_login(self.usr)

        resp = client.get(reverse('reports'))
        resorts_runs = resp.context['resorts_runs']
        self.assertListEqual(resorts_runs, [[['test1', 'Feb 01, 2020', None, ['foo']],
                                            ['test2', 'Jan 31, 2020', None, ['bar']]]])

        # Create a new report for resort2
        rpt = Report.objects.create(date=dt.datetime(2020, 2, 2), resort_id=2)
        rpt.bm_report.runs.add(self.run2)

        resp = client.get(reverse('reports'))
        resorts_runs = resp.context['resorts_runs']
        self.assertListEqual(resorts_runs, [[['test1', 'Feb 01, 2020', None, ['foo']],
                                             ['test2', 'Feb 02, 2020', None, ['bar']]]])

        # Add a third resort
        Resort.objects.create(name='test3')
        rpt = Report.objects.create(date=dt.datetime(2020, 2, 1), resort_id=3)
        rpt.bm_report.runs.add(self.run1)

        resp = client.get(reverse('reports'))
        resorts_runs = resp.context['resorts_runs']
        self.assertListEqual(resorts_runs, [[['test1', 'Feb 01, 2020', None, ['foo']],
                                             ['test2', 'Feb 02, 2020', None, ['bar']]],
                                            [['test3', 'Feb 01, 2020', None, ['foo']]]])

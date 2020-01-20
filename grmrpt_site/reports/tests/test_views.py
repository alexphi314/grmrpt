import json
import datetime as dt
import sys

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

sys.path.append('../grmrpt_fetch')
from grmrpt_fetch.fetch_server import get_resorts_to_notify, create_report
from reports.models import *


class ResortViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.client = APIClient()
        cls.user = User.objects.create_user(username='test', password='foo')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')
        cls.client.credentials(HTTP_AUTHORIZATION='Token ' + cls.token.key)

        cls.rando = User.objects.create_user(username='test2', password='bar')
        cls.rando_token = Token.objects.get(user__username='test2')

        # Create resort object
        cls.resort_data = {'name': 'Beaver Creek TEST', 'location': 'CO', 'report_url': 'foo',
                           'parse_mode': 'tika'}
        resort_response = cls.client.post('/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201

    def test_get(self) -> None:
        """
        Test get returns single resort object
        """
        # Check no user can't GET
        client = APIClient()
        self.assertEqual(client.get('/resorts/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Check logged in user can GET and behavior is as expected
        response = client.get('/resorts/', format='json')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)

        # Add id to resort data
        self.resort_data['id'] = 1
        response[0].pop('sns_arn')
        self.assertDictEqual(response[0], self.resort_data)

        # Check random user has get access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.get('/resorts/').status_code, 200)

    def test_post(self) -> None:
        """
        Test post works
        """
        client = APIClient()

        # Check no user cannot post
        resort_data = {'name': 'Vail TEST', 'location': 'CO', 'report_url': 'bar', 'parse_mode': 'tika'}
        self.assertEqual(client.post('/resorts/', resort_data, format='json').status_code, 401)

        # Check POST behavior for logged in staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.post('/resorts/', resort_data, format='json')

        self.assertEqual(response.status_code, 201)

        response = response.json()
        self.assertTrue('id' in response.keys())
        self.assertTrue('sns_arn' in response.keys())
        # Remove id from dict -> we care that it was returned but not what it is
        response.pop('id')
        response.pop('sns_arn')
        self.assertDictEqual(resort_data, response)

        # Check random user has no post access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.post('/resorts/', resort_data, format='json').status_code, 403)

    def test_put(self) -> None:
        """
        Test put method for resorts
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        response = client.get('/resorts/1/').json()
        response['location'] = 'Kansas'

        # Check no user cannot PUT
        client.credentials()
        self.assertEqual(client.put('/resorts/1/', data=json.dumps(response),
                                    content_type='application/json').status_code, 401)

        # Check staff user PUT works correctly
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        update_response = client.put('/resorts/1/', data=json.dumps(response), content_type='application/json')
        self.assertEqual(update_response.status_code, 200)
        self.assertDictEqual(update_response.json(), response)

        # Check random user has no put access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.put('/resorts/1/', data=json.dumps(response),
                                    content_type='application/json').status_code, 403)

    def test_delete(self) -> None:
        """
        Test delete method for resorts
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Check logged in staff DELETE works
        resort_data = {'name': 'Vail TEST', 'location': 'CO', 'report_url': 'bar'}
        response = client.post('/resorts/', resort_data, format='json')
        id = response.json()['id']

        # Check no user cannot DELETE
        client.credentials()
        self.assertEqual(client.delete('/resorts/{}/'.format(id)).status_code, 401)

        # Check random user has no delete access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.delete('/resorts/{}/'.format(id)).status_code, 403)

        # Check staff delete method
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.delete('/resorts/{}/'.format(id))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(client.get('/resorts/{}/'.format(id)).status_code, 404)

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class RunViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.client = APIClient()
        cls.user = User.objects.create_user(username='test', password='foo')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')
        cls.client.credentials(HTTP_AUTHORIZATION='Token ' + cls.token.key)

        cls.rando = User.objects.create_user(username='test2', password='bar')
        cls.rando_token = Token.objects.get(user__username='test2')

        # Create resort, report, and run objects
        cls.resort_data = {'name': 'Beaver Creek TEST', 'location': 'CO', 'report_url': 'foo'}
        resort_response = cls.client.post('/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201
        cls.resort_url = 'http://testserver/resorts/{}/'.format(resort_response.json()['id'])

        cls.report_data = {'date': dt.datetime.strptime('2020-01-01', '%Y-%m-%d').date(),
                           'resort': cls.resort_url,
                           'runs': []}
        report_response = cls.client.post('/reports/', cls.report_data, format='json')
        assert report_response.status_code == 201
        cls.report_url = 'http://testserver/reports/{}/'.format(report_response.json()['id'])

        cls.run_data = {'name': 'Centennial', 'resort': cls.resort_url,
                        'difficulty': 'blue', 'reports': [cls.report_url]}
        run_response = cls.client.post('/runs/', cls.run_data, format='json')
        assert run_response.status_code == 201

    def test_get(self) -> None:
        """
        Test get method for runs
        """
        client = APIClient()
        # Check no user does not have GET access
        self.assertEqual(client.get('/runs/').status_code, 401)

        # Check logged in staff GEt works
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.get('/runs/')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)
        response = response[0]

        response.pop('id')
        self.assertEqual(response, self.run_data)

        # Check random user has get access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.get('/runs/').status_code, 200)

    def test_post(self) -> None:
        """
        test post method
        """
        client = APIClient()

        # Check no user cannot POST
        run_data = {'name': 'Cresta', 'resort': self.resort_url,
                    'difficulty': 'black', 'reports': [self.report_url]}
        self.assertEqual(client.post('/runs/').status_code, 401)

        # Check logged in staff POST
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        run_response = client.post('/runs/', run_data, format='json')

        self.assertEqual(run_response.status_code, 201)
        run_response = run_response.json()

        run_response.pop('id')
        self.assertEqual(run_response, run_data)

        # Check random user has no post access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.post('/runs/').status_code, 403)

    def test_put(self) -> None:
        """
        test put method
        """
        client = APIClient()
        # check logged in staff put
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        run_response = client.get('/runs/1/', format='json').json()

        report_data = {'date': dt.datetime.strptime('2020-01-01', '%Y-%m-%d').date(),
                       'resort': self.resort_url,
                       'runs': []}
        report_response = client.post('/reports/', report_data, format='json')
        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()
        report_url = 'http://testserver/reports/{}/'.format(report_response['id'])

        run_response['reports'].append(report_url)
        run_response_new = client.put('/runs/1/', data=json.dumps(run_response),
                                           content_type='application/json')
        self.assertEqual(run_response_new.status_code, 200)
        self.assertDictEqual(run_response_new.json(), run_response)

        # Check rando has no put access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.put('/runs/1/', data=json.dumps(run_response),
                                    content_type='application/json').status_code, 403)
        # Check no user has no put access
        client.credentials()
        self.assertEqual(client.put('/runs/1/', data=json.dumps(run_response),
                                    content_type='application/json').status_code, 401)

    def test_delete(self) -> None:
        """
        test delete method
        """
        client = APIClient()
        # Check logged in staff delete works
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        run_data = {'name': 'Cresta', 'resort': self.resort_url,
                    'difficulty': 'black', 'reports': [self.report_url]}
        run_response = client.post('/runs/', run_data, format='json')
        id = run_response.json()['id']

        # Check no user has no delete access
        client.credentials()
        self.assertEqual(client.delete('/runs/{}/'.format(id)).status_code, 401)
        # Check rando user has no delete access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.delete('/runs/{}/'.format(id)).status_code, 403)

        # Check logged in staff delete
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        run_response = client.delete('/runs/{}/'.format(id))
        self.assertEqual(run_response.status_code, 204)

        self.assertEqual(client.get('/runs/{}/'.format(id)).status_code, 404)

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class ReportViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.client = APIClient()
        cls.user = User.objects.create_user(username='test', password='foo')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')
        cls.client.credentials(HTTP_AUTHORIZATION='Token ' + cls.token.key)

        cls.rando = User.objects.create_user(username='test2', password='bar')
        cls.rando.is_staff = False
        cls.user.save()
        cls.rando_token = Token.objects.get(user__username='test2')

        # Create report, run, and resort objects
        cls.resort_data = {'name': 'Beaver Creek TEST', 'location': 'CO', 'report_url': 'foo'}
        resort_response = cls.client.post('/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201
        cls.resort_url = 'http://testserver/resorts/{}/'.format(resort_response.json()['id'])

        cls.run_data1 = {'name': 'Centennial', 'resort': cls.resort_url,
                        'difficulty': 'blue', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data1, format='json')
        assert run_response.status_code == 201
        cls.run1_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

        cls.run_data2 = {'name': 'Stone Creek Chutes', 'resort': cls.resort_url,
                         'difficulty': 'black', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data2, format='json')
        assert run_response.status_code == 201
        cls.run2_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

        cls.run_data3 = {'name': 'Double Diamond', 'resort': cls.resort_url,
                         'difficulty': 'black', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data3, format='json')
        assert run_response.status_code == 201
        cls.run3_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

        cls.report_data = {'date': '2020-01-01',
                           'resort': cls.resort_url,
                           'runs': [cls.run1_url]}
        report_response = cls.client.post('/reports/', cls.report_data, format='json')
        cls.report_url = 'http://testserver/reports/{}/'.format(report_response.json()['id'])
        assert report_response.status_code == 201

    def test_run_report_link(self) -> None:
        """
        test run objects link back to report after report object created linked to them
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        for run_url in [self.run1_url, self.run2_url]:
            run_response = client.get(run_url)
            self.assertEqual(run_response.status_code, 200)
            run_response = run_response.json()
            if run_url == self.run1_url:
                self.assertEqual(len(run_response['reports']), 1)
                self.assertEqual(run_response['reports'][0], self.report_url)
            else:
                self.assertEqual(len(run_response['reports']), 0)

    def assert_bmreport_report_equal(self, bm_report_response, report_response, expected_runs,
                                     report_url) -> None:
        """
        Assert the bm_report response and report response match correctly

        :param bm_report_response: bm_report data
        :param report_response: report data
        :param expected_runs: list of expected run urls in bm_report_response
        :param report_url: hyperlink to report object
        """
        self.assertEqual(bm_report_response['resort'], report_response['resort'])
        self.assertEqual(bm_report_response['date'], report_response['date'])
        self.assertEqual(bm_report_response['full_report'], report_url)
        self.assertListEqual(bm_report_response['runs'], expected_runs)

    def test_report_bmreport_post(self) -> None:
        """
        test that generated bmreport from new report object works as intended
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Check the original bm_report has no runs linked
        bmreport_response = client.get('/bmreports/1/', format='json')
        self.assertEqual(bmreport_response.status_code, 200)
        self.assert_bmreport_report_equal(bmreport_response.json(), self.report_data, [],
                                          'http://testserver/reports/1/')

        # Create a second report the day after the original one
        report_data = {'date': '2020-01-02',
                       'resort': self.resort_url,
                       'runs': [self.run1_url, self.run3_url]}
        report_response = client.post('/reports/', report_data, format='json')
        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()
        report_url = 'http://testserver/reports/{}/'.format(report_response['id'])

        # Check BMreport objects created correctly
        bmreport_response = client.get('/bmreports/', format='json')
        self.assertEqual(bmreport_response.status_code, 200)
        bmreport_response = bmreport_response.json()
        self.assertEqual(len(bmreport_response), 2)

        bmreport_response = client.get(report_response['bm_report']).json()
        self.assert_bmreport_report_equal(bmreport_response, report_data, [self.run3_url], report_url)

        # Create a third report the day after the original one
        report_data2 = {'date': '2020-01-03',
                       'resort': self.resort_url,
                       'runs': [self.run2_url, self.run1_url]}
        report_response = client.post('/reports/', report_data2, format='json')
        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()
        report_url2 = 'http://testserver/reports/{}/'.format(report_response['id'])
        bmreport_response = client.get(report_response['bm_report']).json()

        self.assert_bmreport_report_equal(bmreport_response, report_data2, [self.run2_url], report_url2)

        # Generate a week's worth of report objects
        report_data3 = {'date': '2020-01-04',
                        'resort': self.resort_url,
                        'runs': [self.run3_url, self.run1_url]}
        report_response3 = client.post('/reports/', report_data3, format='json').json()
        report_url3 = 'http://testserver/reports/{}/'.format(report_response3['id'])

        report_data4 = {'date': '2020-01-05',
                        'resort': self.resort_url,
                        'runs': [self.run1_url]}
        report_response4 = client.post('/reports/', report_data4, format='json').json()
        report_url4 = 'http://testserver/reports/{}/'.format(report_response4['id'])

        report_data5 = {'date': '2020-01-06',
                        'resort': self.resort_url,
                        'runs': [self.run3_url, self.run1_url]}
        report_response5 = client.post('/reports/', report_data5, format='json').json()
        report_url5 = 'http://testserver/reports/{}/'.format(report_response5['id'])

        report_data6 = {'date': '2020-01-07',
                        'resort': self.resort_url,
                        'runs': [self.run3_url]}
        report_response6 = client.post('/reports/', report_data6, format='json').json()
        report_url6 = 'http://testserver/reports/{}/'.format(report_response6['id'])

        report_data7 = {'date': '2020-01-08',
                        'resort': self.resort_url,
                        'runs': [self.run3_url, self.run1_url, self.run2_url]}
        report_response7 = client.post('/reports/', report_data7, format='json').json()
        report_url7 = 'http://testserver/reports/{}/'.format(report_response7['id'])

        report_data8 = {'date': '2019-12-31',
                        'resort': self.resort_url,
                        'runs': [self.run2_url]}
        report_response8 = client.post('/reports/', report_data8, format='json').json()
        report_url8 = 'http://testserver/reports/{}/'.format(report_response8['id'])

        # Check that the bmreport for report7 has the expected values
        bmreport_response = client.get(report_response7['bm_report']).json()
        self.assert_bmreport_report_equal(bmreport_response, report_data7, [self.run2_url], report_url7)

        # Adjust one day to include a run2 groom -> run2 no longer under 30% groom rate
        report_response = client.get(report_url6).json()
        report_response['runs'].append(self.run2_url)
        client.put(report_url6, data=json.dumps(report_response), content_type='application/json')
        # TODO: Updating an upstream report does not cause BMReport object to automatically update; must put
        # corresponding report object to get BMReport to update
        client.put(report_url7, data=json.dumps(report_response7), content_type='application/json')
        bmreport_response = client.get(report_response7['bm_report']).json()
        self.assert_bmreport_report_equal(bmreport_response, report_data7, [], report_url7)

        # Delete the posted reports
        response = client.delete(report_url)
        self.assertEqual(response.status_code, 204)
        response = client.delete(report_url2)
        self.assertEqual(response.status_code, 204)
        client.delete(report_url3)
        client.delete(report_url4)
        client.delete(report_url5)
        client.delete(report_url6)
        client.delete(report_url7)
        client.delete(report_url8)
        self.assertEqual(len(client.get('/reports/').json()), 1)

    def test_report_bmreport_put(self) -> None:
        """
        test report put also updated bmreport object accordingly
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Create a second report the day after the original one
        report_data = {'date': '2020-01-02',
                       'resort': self.resort_url,
                       'runs': [self.run1_url]}
        report_response = client.post('/reports/', report_data, format='json').json()
        report_url = 'http://testserver/reports/{}/'.format(report_response['id'])

        # Create a third report the day after the original one
        report_data2 = {'date': '2020-01-03',
                        'resort': self.resort_url,
                        'runs': [self.run2_url, self.run1_url]}
        report_response2 = client.post('/reports/', report_data2, format='json').json()
        report_url2 = 'http://testserver/reports/{}/'.format(report_response2['id'])

        # Update the second and third report to include run3
        report_data['runs'].append(self.run3_url)
        report_data2['runs'].append(self.run3_url)

        update_response = client.put(report_url, data=json.dumps(report_data),
                                          content_type='application/json')
        self.assertEqual(update_response.status_code, 200)
        update_response2 = client.put(report_url2, data=json.dumps(report_data2),
                                           content_type='application/json')
        self.assertEqual(update_response2.status_code, 200)

        # Check updated HDreport objects are right
        bm_report2 = client.get(report_response2['bm_report'], format='json').json()
        self.assert_bmreport_report_equal(bm_report2, report_data2, [self.run2_url],
                                          report_url2)

    def test_get(self) -> None:
        """
        test get method for report
        """
        client = APIClient()
        # Check anon user doesn't have GET access
        self.assertEqual(client.get('/reports/').status_code, 401)

        # Check staff user has GET
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.get('/reports/')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)
        response = response[0]

        response.pop('id')
        response.pop('bm_report')
        self.assertEqual(response, self.report_data)

        # Check rando user has GEt
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.get('/reports/').status_code, 200)

    def test_post(self) -> None:
        """
        test post method of report
        """
        client = APIClient()

        # Check anon user has no POST access
        report_data = {'date': '2019-12-31',
                       'resort': self.resort_url,
                       'runs': [self.run1_url]}
        self.assertEqual(client.post('/reports/', report_data, format='json').status_code, 401)

        # Check staff user has POST and works correctly
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        report_response = client.post('/reports/', report_data, format='json')

        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()

        # Check rando user has no POST access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.post('/reports/', report_data, format='json').status_code, 403)

        # Delete the posted report
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        delete_resp = client.delete('/reports/{}/'.format(report_response['id']))
        assert delete_resp.status_code == 204

        report_response.pop('id')
        report_response.pop('bm_report')
        self.assertEqual(report_response, report_data)

    def test_put(self) -> None:
        """
        test put method of report
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        report_response = client.get('/reports/1/', format='json').json()
        report_response['runs'] = [self.run1_url]

        # Check anon user has no PUT access
        client.credentials()
        self.assertEqual(client.put('/reports/1/', format='json').status_code, 401)
        # Check rando user has no PUT access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.put('/reports/1/', format='json').status_code, 403)

        # Check staff user PUT works
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        run_response_new = client.put('/reports/1/', data=json.dumps(report_response),
                                           content_type='application/json')
        self.assertEqual(run_response_new.status_code, 200)
        self.assertDictEqual(run_response_new.json(), report_response)

    def test_delete(self) -> None:
        """
        test delete method
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        report_data = {'date': '2019-12-31',
                       'resort': self.resort_url,
                       'runs': [self.run1_url]}
        report_response = client.post('/reports/', report_data, format='json')
        id = report_response.json()['id']

        # Check anon user has no DELETE access
        client.credentials()
        self.assertEqual(client.delete('/reports/{}/'.format(id)).status_code, 401)
        # Check rando user has no DELETE access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.delete('/reports/{}/'.format(id)).status_code, 403)

        # Chedk staff DELETE works
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        report_response = client.delete('/reports/{}/'.format(id))
        self.assertEqual(report_response.status_code, 204)

        self.assertEqual(client.get('/reports/{}/'.format(id)).status_code, 404)

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class BMReportViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.client = APIClient()
        cls.user = User.objects.create_user(username='test', password='foo')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')
        cls.client.credentials(HTTP_AUTHORIZATION='Token ' + cls.token.key)

        cls.rando = User.objects.create_user(username='test2', password='bar')
        cls.rando_token = Token.objects.get(user__username='test2')

        # Create report, resort, run objects
        cls.resort_data = {'name': 'Beaver Creek TEST', 'location': 'CO', 'report_url': 'foo'}
        resort_response = cls.client.post('/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201
        cls.resort_url = 'http://testserver/resorts/{}/'.format(resort_response.json()['id'])

        cls.run_data1 = {'name': 'Centennial', 'resort': cls.resort_url,
                         'difficulty': 'blue', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data1, format='json')
        assert run_response.status_code == 201
        cls.run1_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

        cls.run_data2 = {'name': 'Stone Creek Chutes', 'resort': cls.resort_url,
                         'difficulty': 'black', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data2, format='json')
        assert run_response.status_code == 201
        cls.run2_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

        cls.run_data3 = {'name': 'Double Diamond', 'resort': cls.resort_url,
                         'difficulty': 'black', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data3, format='json')
        assert run_response.status_code == 201
        cls.run3_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

        cls.report_data = {'date': '2020-01-01',
                           'resort': cls.resort_url,
                           'runs': [cls.run1_url, cls.run2_url]}
        report_response = cls.client.post('/reports/', cls.report_data, format='json')
        cls.report_url = 'http://testserver/reports/{}/'.format(report_response.json()['id'])
        assert report_response.status_code == 201

        cls.bmreport_data = {
            'date': '2020-01-01',
            'resort': cls.resort_url,
            'runs': [],
            'full_report': cls.report_url,
            'notification': None
        }

    def test_get(self) -> None:
        """
        test get method works correctly
        """
        # Check anon user does not have GET
        client = APIClient()
        self.assertEqual(client.get('/bmreports/').status_code, 401)
        # Check rando user has GET
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.get('/bmreports/').status_code, 200)

        # Check staff GET works as expected
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        response = client.get('/bmreports/')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)
        response = response[0]

        response.pop('id')
        self.assertEqual(response, self.bmreport_data)

    def test_post(self) -> None:
        """
        test post method does not work
        """
        client = APIClient()
        # Check anon user has no POST
        self.assertEqual(client.post('/bmreports/', self.bmreport_data, format='json').status_code, 401)
        # Check rando user has no POSt
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.post('/bmreports/', self.bmreport_data, format='json').status_code, 403)

        # Check staff POSt works as expected
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        response = client.post('/bmreports/', self.bmreport_data, format='json')
        self.assertEqual(response.status_code, 405)

    def test_put(self) -> None:
        """
        test put method
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        report_response = client.get('/bmreports/1/', format='json').json()
        report_response['runs'] = [self.run1_url]

        # Check anon user has no PUT
        client.credentials()
        self.assertEqual(client.put('/bmreports/1/', data=json.dumps(report_response),
                                           content_type='application/json').status_code, 401)
        # Check rando user has no PUT
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.put('/bmreports/1/', data=json.dumps(report_response),
                                    content_type='application/json').status_code, 403)

        # Check staff PUT works as expected
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        run_response_new = client.put('/bmreports/1/', data=json.dumps(report_response),
                                           content_type='application/json')
        self.assertEqual(run_response_new.status_code, 200)
        self.assertDictEqual(run_response_new.json(), report_response)

    def test_delete(self) -> None:
        """
        test delete method does not work
        """
        client = APIClient()
        # Check anon DELETE does not work
        self.assertEqual(client.delete('/bmreports/1/').status_code, 401)
        # Check rando has no DELETE
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.delete('/bmreports/1/').status_code, 403)

        # Check that staff DELETE works as expected
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        report_response = client.delete('/bmreports/1/')
        self.assertEqual(report_response.status_code, 405)

        # Test that deleting report object deletes BMReport object
        self.assertEqual(len(client.get('/bmreports/').json()), 1)
        report_response = client.delete(self.report_url)
        self.assertEqual(report_response.status_code, 204)

        bmreport_response = client.get('/bmreports/')
        self.assertEqual(bmreport_response.status_code, 200)

        bmreport_response = bmreport_response.json()
        self.assertEqual(len(bmreport_response), 0)

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class UserViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.user = User.objects.create_user(username='test', password='foo', email='AP_TEST')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')

        cls.rando = User.objects.create_user(username='test2', password='bar', email='AP_TEST')
        cls.rando_token = Token.objects.get(user__username='test2')

    def test_get(self) -> None:
        """
        test get method works as expected
        """
        # Check GET fails for anon and rando user
        client = APIClient()
        self.assertEqual(client.get('/users/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.get('/users/').status_code, 403)

        # Check GET works for staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.get('/users/')
        self.assertEqual(response.status_code, 200)
        response = response.json()

        self.assertEqual(len(response), 2)

        self.assertTrue('bmg_user' in response[0].keys())
        self.assertEqual(response[0]['username'], 'test')
        self.assertEqual(response[0]['email'], 'AP_TEST')
        self.assertTrue(response[0]['is_staff'])

        self.assertTrue('bmg_user' in response[1].keys())
        self.assertEqual(response[1]['username'], 'test2')
        self.assertEqual(response[1]['email'], 'AP_TEST')
        self.assertFalse(response[1]['is_staff'])

    def test_post(self) -> None:
        """
        test post method works
        """
        # Check POST fails for anon and rando user
        client = APIClient()
        self.assertEqual(client.post('/users/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.post('/users/').status_code, 403)

        # Check BMGUser objects created
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.assertEqual(len(client.get('/bmgusers/').json()), 2)

        # Check POST works for staff user

        user_data = {
            'username': 'test3',
            'email': 'AP_TEST@gmail.com',
            'password': 'secret_password'
        }
        response = client.post('/users/', user_data, format='json')
        self.assertEqual(response.status_code, 201)
        response = response.json()
        user_id = response['id']
        user_url = '/users/{}/'.format(user_id)

        response.pop('id')
        response.pop('bmg_user')
        self.assertFalse(response['is_staff'])
        self.assertEqual(response['username'], user_data['username'])
        self.assertEqual(response['email'], user_data['email'])

        # Check BMGUser object created
        self.assertEqual(client.get('/bmgusers/{}/'.format(user_id)).status_code, 200)
        self.assertEqual(len(client.get('/bmgusers/').json()), 3)

        # Delete the posted user
        client.delete(user_url)

    def test_put(self) -> None:
        """
        test put method
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        user_data = {
            'username': 'test3',
            'email': 'AP_TEST@gmail.com',
            'password': 'secret_password'
        }
        response = client.post('/users/', user_data, format='json')
        response = response.json()
        user_url = '/users/{}/'.format(response['id'])

        response['email'] = 'AP_TEST@gmail.com'

        # Check put fails for anon and rando users
        client.credentials()
        self.assertEqual(client.put(user_url, data=json.dumps(response),
                                    content_type='application/json').status_code,
                         401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.put(user_url, data=json.dumps(response),
                                    content_type='application/json').status_code,
                         403)

        # Check put works for staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.put(user_url, data=json.dumps(response), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertFalse(response['is_staff'])
        self.assertEqual(response['username'], user_data['username'])
        self.assertEqual(response['email'], 'AP_TEST@gmail.com')

        client.delete(user_url)

    def test_delete(self) -> None:
        """
        test delete method
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        user_data = {
            'username': 'test3',
            'email': 'AP_TEST@gmail.com',
            'password': 'secret_password'
        }
        response = client.post('/users/', user_data, format='json')
        response = response.json()
        user_url = '/users/{}/'.format(response['id'])

        # Check delete fails for anon or rando user
        client.credentials()
        self.assertEqual(client.delete(user_url).status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.delete(user_url).status_code, 403)

        # Check delete works for staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.delete(user_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(client.get(user_url).status_code, 404)

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class BMGUserViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.user = User.objects.create_user(username='test', password='foo', email='AP_TEST')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')

        cls.rando = User.objects.create_user(username='test2', password='bar', email='AP_TEST')
        cls.rando_token = Token.objects.get(user__username='test2')

        # Create report, resort, run objects
        cls.client = APIClient()
        cls.client.credentials(HTTP_AUTHORIZATION='Token ' + cls.token.key)
        cls.resort_data = {'name': 'Beaver Creek TEST', 'location': 'CO', 'report_url': 'foo'}
        resort_response = cls.client.post('/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201
        cls.resort_url = 'http://testserver/resorts/{}/'.format(resort_response.json()['id'])

        cls.run_data1 = {'name': 'Centennial', 'resort': cls.resort_url,
                         'difficulty': 'blue', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data1, format='json')
        assert run_response.status_code == 201
        cls.run1_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

    def test_get(self) -> None:
        """
        test get method
        """
        # Check get fails for anon or rando user
        client = APIClient()
        self.assertEqual(client.get('/bmgusers/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.get('/bmgusers/').status_code, 403)

        # Check GET works for staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.get('/bmgusers/')
        self.assertEqual(response.status_code, 200)
        response = response.json()

        self.assertEqual(response[0]['id'], 1)
        self.assertEqual(response[0]['phone'], None)
        self.assertDictEqual(response[0]['user'], {'id': 1, 'username': 'test', 'email': 'AP_TEST',
                                                'bmg_user': 'http://testserver/bmgusers/1/',
                                                'is_staff': True})
        self.assertListEqual(response[0]['favorite_runs'], [])
        self.assertListEqual(response[0]['resorts'], [])
        self.assertIsNone(response[0]['contact_days'])

        self.assertEqual(response[1]['id'], 2)
        self.assertEqual(response[1]['phone'], None)
        self.assertDictEqual(response[1]['user'], {'id': 2, 'username': 'test2', 'email': 'AP_TEST',
                                                'bmg_user': 'http://testserver/bmgusers/2/',
                                                'is_staff': False})
        self.assertListEqual(response[1]['favorite_runs'], [])
        self.assertListEqual(response[1]['resorts'], [])
        self.assertIsNone(response[1]['contact_days'])

    def test_post(self) -> None:
        """
        test post method
        """
        client = APIClient()

        # Check POST fails for anon and rando users
        self.assertEqual(client.post('/bmgusers/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.post('/bmgusers/').status_code, 403)

        # Check POST fails for staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.get('/bmgusers/1/')
        self.assertEqual(client.post('/bmgusers/', response, content_type='json').status_code, 405)

    def test_put(self) -> None:
        """
        test put method
        """
        # Create new user
        User.objects.create_user(username='test3', password='bus', email='AP_TEST')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.get('/bmgusers/3/').json()


        # Add fields
        response.pop('sub_arn')
        response['phone'] = '1800-290-7856'
        response['favorite_runs'] = [self.run1_url]
        response['resorts'] = [self.resort_url]

        # Check PUT fails for anon and rando users
        client.credentials()
        self.assertEqual(client.put('/bmgusers/3/',
                                    data=json.dumps(response), content_type='application/json').status_code,
                         401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.put('/bmgusers/3/',
                                    data=json.dumps(response), content_type='application/json').status_code,
                         403)

        # Check PUT works for staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        put_response = client.put('/bmgusers/3/', data=json.dumps(response), content_type='application/json')
        self.assertEqual(put_response.status_code, 200)

        put_response = put_response.json()
        put_response.pop('sub_arn')
        self.assertDictEqual(response, put_response)
        client.delete('/users/3/')

    def test_delete(self) -> None:
        """
        test delete method
        """
        # Create new user
        User.objects.create_user(username='test3', password='bus', email='AP_TEST')
        client = APIClient()

        # Check delete fails for rando and anon
        self.assertEqual(client.delete('/bmgusers/3/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.delete('/bmgusers/3/').status_code, 403)

        # Check delete fails for staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.assertEqual(client.delete('/bmgusers/3/').status_code, 405)

        # Check delete works if User object deleted
        resp = client.delete('/users/3/')
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(client.get('/bmgusers/3/').status_code, 404)
        self.assertEqual(len(client.get('/bmgusers/').json()), 2)

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class NotifyUsersTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.user = User.objects.create_user(username='test', password='foo', email='AP_TEST')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')

        cls.client = APIClient()
        cls.client.credentials(HTTP_AUTHORIZATION='Token ' + cls.token.key)

        # Create report, resort, run objects
        cls.resort_data = {'name': 'Beaver Creek TEST', 'location': 'CO', 'report_url': 'foo'}
        resort_response = cls.client.post('/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201
        cls.resort_url = 'http://testserver/resorts/{}/'.format(resort_response.json()['id'])

        cls.resort_data2 = {'name': 'Vail TEST', 'location': 'CO', 'report_url': 'foo'}
        resort_response2 = cls.client.post('/resorts/', cls.resort_data2, format='json')
        assert resort_response2.status_code == 201
        cls.resort_url2 = 'http://testserver/resorts/{}/'.format(resort_response2.json()['id'])

        cls.run_data1 = {'name': 'Centennial', 'resort': cls.resort_url,
                         'difficulty': 'blue', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data1, format='json')
        assert run_response.status_code == 201
        cls.run1_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

        cls.run_data2 = {'name': 'Stone Creek Chutes', 'resort': cls.resort_url,
                         'difficulty': 'black', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data2, format='json')
        assert run_response.status_code == 201
        cls.run2_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

        cls.run_data3 = {'name': 'Double Diamond', 'resort': cls.resort_url2,
                         'difficulty': 'black', 'reports': []}
        run_response = cls.client.post('/runs/', cls.run_data3, format='json')
        assert run_response.status_code == 201
        cls.run3_url = 'http://testserver/runs/{}/'.format(run_response.json()['id'])

        cls.report_data = {'date': '2019-12-31',
                           'resort': cls.resort_url,
                           'runs': [cls.run1_url, cls.run2_url]}
        report_response = cls.client.post('/reports/', cls.report_data, format='json')
        assert report_response.status_code == 201

        cls.report_data2 = {'date': '2019-12-31',
                           'resort': cls.resort_url2,
                           'runs': [cls.run3_url]}
        report_response = cls.client.post('/reports/', cls.report_data2, format='json')
        assert report_response.status_code == 201
        cls.resort2_report_url = 'http://testserver/bmreports/{}/'.format(report_response.json()['id'])
        cls.resort2_id = report_response.json()['id']
        # Link run to bmr
        bmr = BMReport.objects.get(pk=2)
        bmr.runs.add(Run.objects.get(pk=1))

        # Create notification
        Notification.objects.create(bm_report=Report.objects.get(pk=1).bm_report)

    def test_func(self) -> None:
        """
        check function returns expected list of users
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        def get_wrapper(x: str):
            return client.get('/{}'.format(x)).json()
            # else:
            #     return client.get(x).json()

        resorts = get_resorts_to_notify(get_wrapper, 'http://testserver')
        self.assertListEqual(resorts, [self.resort2_report_url])

        # Add report on 1-2
        report_data = {'date': '2020-01-02',
                       'resort': self.resort_url,
                       'runs': [self.run1_url, self.run2_url]}
        report_response = client.post('/reports/', report_data, format='json')
        assert report_response.status_code == 201
        report_url = 'http://testserver/bmreports/{}/'.format(report_response.json()['id'])
        resorts = get_resorts_to_notify(get_wrapper, 'http://testserver')
        self.assertListEqual(resorts, [self.resort2_report_url])

        # Add run to BMR and check resort is now on notification list
        bmr = BMReport.objects.get(pk=client.get(report_response.json()['bm_report']).json()['id'])
        bmr.runs.add(Run.objects.get(pk=1))
        resorts = get_resorts_to_notify(get_wrapper, 'http://testserver')
        self.assertListEqual(resorts, [report_url, self.resort2_report_url])

        # Add report on 1-6
        report_data = {'date': '2020-01-06',
                       'resort': self.resort_url,
                       'runs': [self.run1_url, self.run2_url]}
        report_response = client.post('/reports/', report_data, format='json')
        assert report_response.status_code == 201
        report_url = 'http://testserver/bmreports/{}/'.format(report_response.json()['id'])
        resort1_id = report_response.json()['id']
        bmr = BMReport.objects.get(pk=client.get(report_response.json()['bm_report']).json()['id'])
        bmr.runs.add(Run.objects.get(pk=1))

        # With new report, notify resort2 and updated report
        resorts = get_resorts_to_notify(get_wrapper, 'http://testserver')
        self.assertListEqual(resorts, [report_url, self.resort2_report_url])

        # Notify both
        Notification.objects.create(bm_report_id=resort1_id)
        Notification.objects.create(bm_report_id=self.resort2_id)

        # Confirm no notifications to go out
        resorts = get_resorts_to_notify(get_wrapper, 'http://testserver')
        self.assertListEqual(resorts, [])

        # Create a bogus report with no runs attached
        report_data = {'date': '2020-01-07',
                       'resort': self.resort_url,
                       'runs': []}
        report_response = client.post('/reports/', report_data, format='json')
        assert report_response.status_code == 201
        # Confirm no notifications to go out
        resorts = get_resorts_to_notify(get_wrapper, 'http://testserver')
        self.assertListEqual(resorts, [])

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class NotificationViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.user = User.objects.create_user(username='test', password='foo', email='AP_TEST')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')

        cls.rando = User.objects.create_user(username='user1', password='bar')
        cls.rando_token = Token.objects.get(user__username='user1')

        # Create report, resort, etc
        cls.resort = Resort.objects.create(name='BC TEST', location='CO', report_url='foo')
        cls.report = Report.objects.create(date=dt.datetime(2020, 1, 1).date(), resort=cls.resort)
        cls.resort2 = Resort.objects.create(name='Vail TEST', location='CO', report_url='foo')
        cls.report2 = Report.objects.create(date=dt.datetime(2020, 1, 2).date(), resort=cls.resort2)
        cls.report3 = Report.objects.create(date=dt.datetime(2020, 1, 3).date(), resort=cls.resort2)

        # Create notification
        cls.notification = Notification.objects.create(bm_report=cls.report.bm_report)

    def test_get(self) -> None:
        """
        test get method
        """
        # Check get fails for anon or rando user
        client = APIClient()
        self.assertEqual(client.get('/notifications/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.get('/notifications/').status_code, 403)

        # Check GET works for staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.get('/notifications/')
        self.assertEqual(response.status_code, 200)
        response = response.json()[0]

        self.assertEqual(response['id'], 1)
        self.assertEqual(response['bm_report'], 'http://testserver/bmreports/1/')
        self.assertTrue('sent' in response.keys())

        # Check notification linked on bm_report request
        response = client.get('/bmreports/1/').json()
        self.assertEqual(response['notification'], 'http://testserver/notifications/1/')

        # Create notification
        rpt = Report.objects.create(date=dt.datetime(2020, 1, 5).date(), resort=self.resort)
        Notification.objects.create(bm_report=rpt.bm_report)

        # Create notification, test query params work for resort
        Notification.objects.create(bm_report=self.report3.bm_report)
        query_response = client.get('/notifications/?resort=Vail%20TEST').json()
        self.assertEqual(len(query_response), 1)
        self.assertEqual(query_response[0]['bm_report'], 'http://testserver/bmreports/3/')

        # Create notification, test query params work for report
        Notification.objects.create(bm_report=self.report2.bm_report)
        query_response = client.get('/notifications/?report_date=2020-01-02').json()
        self.assertEqual(len(query_response), 1)
        self.assertEqual(query_response[0]['bm_report'], 'http://testserver/bmreports/2/')
        query_response = client.get('/notifications/?bm_pk=2').json()
        self.assertEqual(len(query_response), 1)
        self.assertEqual(query_response[0]['bm_report'], 'http://testserver/bmreports/2/')

        # Check combined query works - no results
        query_response = client.get('/notifications/?report_date=2020-01-02&resort=BC').json()
        self.assertEqual(len(query_response), 0)

    def test_post(self) -> None:
        """
        test post method
        """
        client = APIClient()

        # Check POST fails for anon and rando users
        self.assertEqual(client.post('/notifications/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.post('/notifications/').status_code, 403)

        # Check post works for staff
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        rpt = Report.objects.create(date=dt.datetime(2020, 1, 6).date(), resort=self.resort2)
        post_data = {
            'bm_report': 'http://testserver/bmreports/{}/'.format(rpt.id),
        }
        response = client.post('/notifications/', post_data, format='json')
        self.assertEqual(response.status_code, 201)
        response = response.json()
        response_url = 'http://testserver/notifications/{}/'.format(response['id'])
        response.pop('id')
        response.pop('sent')

        self.assertDictEqual(response, post_data)

        # Delete posted notification
        client.delete(response_url)

    def test_put(self) -> None:
        """
        test put method
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        notification = client.get('/notifications/').json()[0]

        # Update data
        notification['bm_report'] = 'http://testserver/bmreports/2/'

        # Check PUT fails for rando and anon user
        client.credentials()
        response = client.put('/notifications/1/', data=json.dumps(notification), content_type='application/json')
        self.assertEqual(response.status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        response = client.put('/notifications/1/', data=json.dumps(notification), content_type='application/json')
        self.assertEqual(response.status_code, 403)

        # Check PUT works for staff
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.put('/notifications/1/', data=json.dumps(notification), content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.assertDictEqual(response.json(), notification)

    def test_delete(self) -> None:
        """
        test delete method
        """
        client = APIClient()

        # Create notification
        report4 = Report.objects.create(date=dt.datetime(2020, 1, 4).date(), resort=self.resort2)
        Notification.objects.create(bm_report=report4.bm_report)

        # Check delete fails for anon or rando
        self.assertEqual(client.delete('/notifications/2/').status_code, 401)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.delete('/notifications/2/').status_code, 403)

        # Check delete works for staff
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.delete('/notifications/2/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(client.get('/notifications/2/').status_code, 404)
        self.assertEqual(len(client.get('/notifications/').json()), 1)

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class FetchCreateReportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.user = User.objects.create_user(username='test', password='foo', email='AP_TEST')
        cls.user.is_staff = True
        cls.user.save()
        cls.token = Token.objects.get(user__username='test')

        # Create report, resort, etc
        cls.resort = Resort.objects.create(name='BC TEST', location='CO', report_url='foo')
        cls.report = Report.objects.create(date=dt.datetime(2020, 1, 1).date(), resort=cls.resort)
        cls.run1 = Run.objects.create(name='Ripsaw', resort=cls.resort)
        cls.run2 = Run.objects.create(name='Centennial', resort=cls.resort)
        cls.run3 = Run.objects.create(name='Larkspur', resort=cls.resort)

    def test_create_report(self) -> None:
        """
        test report populated with groomed runs
        """
        date = dt.datetime(2020, 1, 1).date()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        get_api = lambda x, y, z: client.get('/{}'.format(x)).json()
        create_report(date, ['Ripsaw', 'Centennial'], 1, 'http://testserver', self.token.key, client, get_api)

        self.assertListEqual([self.run1, self.run2], list(self.report.runs.all()))

    def test_update_report(self) -> None:
        date = dt.datetime(2020, 1, 1).date()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        get_api = lambda x, y, z: client.get('/{}'.format(x)).json()
        create_report(date, ['Ripsaw', 'Larkspur'], 1, 'http://testserver', self.token.key, client, get_api)

        self.assertListEqual([self.run1, self.run3], list(self.report.runs.all()))

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()

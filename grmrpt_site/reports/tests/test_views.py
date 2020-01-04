import json
import datetime as dt

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token


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
        cls.resort_data = {'name': 'Beaver Creek', 'location': 'CO', 'report_url': 'foo'}
        resort_response = cls.client.post('/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201

    def test_get(self) -> None:
        """
        Test get returns single resort object
        """
        # Check no user can GET
        client = APIClient()
        self.assertEqual(client.get('/resorts/').status_code, 200)
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Check logged in user can GET and behavior is as expected
        response = client.get('/resorts/', format='json')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)

        # Add id to resort data
        self.resort_data['id'] = 1
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
        resort_data = {'name': 'Vail', 'location': 'CO', 'report_url': 'bar'}
        self.assertEqual(client.post('/resorts/', resort_data, format='json').status_code, 401)

        # Check POST behavior for logged in staff user
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.post('/resorts/', resort_data, format='json')

        self.assertEqual(response.status_code, 201)

        response = response.json()
        self.assertTrue('id' in response.keys())
        # Remove id from dict -> we care that it was returned but not what it is
        response.pop('id')
        self.assertDictEqual(resort_data, response)

        # Check random user has no post access
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.post('/resorts/', resort_data, format='json').status_code, 403)

    def test_put(self) -> None:
        """
        Test put method for resorts
        """
        client = APIClient()

        response = client.get('/resorts/1/').json()
        response['location'] = 'Kansas'

        # Check no user cannot PUT
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
        resort_data = {'name': 'Vail', 'location': 'CO', 'report_url': 'bar'}
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
        cls.resort_data = {'name': 'Beaver Creek', 'location': 'CO', 'report_url': 'foo'}
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
        # Check no user has GET access
        self.assertEqual(client.get('/runs/').status_code, 200)

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
        cls.resort_data = {'name': 'Beaver Creek', 'location': 'CO', 'report_url': 'foo'}
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

    def assert_hdreport_report_equal(self, hd_report_response, report_response, expected_runs,
                                     report_url) -> None:
        """
        Assert the hd_report response and report response match correctly

        :param hd_report_response: hd_report data
        :param report_response: report data
        :param expected_runs: list of expected run urls in hd_report_response
        :param report_url: hyperlink to report object
        """
        self.assertEqual(hd_report_response['resort'], report_response['resort'])
        self.assertEqual(hd_report_response['date'], report_response['date'])
        self.assertEqual(hd_report_response['full_report'], report_url)
        self.assertListEqual(hd_report_response['runs'], expected_runs)

    def test_report_hdreport_post(self) -> None:
        """
        test that generated hdreport from new report object works as intended
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Check the original hd_report has no runs linked
        hdreport_response = client.get('/hdreports/1/', format='json')
        self.assertEqual(hdreport_response.status_code, 200)
        self.assert_hdreport_report_equal(hdreport_response.json(), self.report_data, [],
                                          'http://testserver/reports/1/')

        # Create a second report the day after the original one
        report_data = {'date': '2020-01-02',
                       'resort': self.resort_url,
                       'runs': [self.run1_url, self.run3_url]}
        report_response = client.post('/reports/', report_data, format='json')
        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()
        report_url = 'http://testserver/reports/{}/'.format(report_response['id'])

        # Check HDreport objects created correctly
        hdreport_response = client.get('/hdreports/', format='json')
        self.assertEqual(hdreport_response.status_code, 200)
        hdreport_response = hdreport_response.json()
        self.assertEqual(len(hdreport_response), 2)

        hdreport_response = client.get(report_response['hd_report']).json()
        self.assert_hdreport_report_equal(hdreport_response, report_data, [self.run3_url], report_url)

        # Create a third report the day after the original one
        report_data2 = {'date': '2020-01-03',
                       'resort': self.resort_url,
                       'runs': [self.run2_url, self.run1_url]}
        report_response = client.post('/reports/', report_data2, format='json')
        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()
        report_url2 = 'http://testserver/reports/{}/'.format(report_response['id'])
        hdreport_response = client.get(report_response['hd_report']).json()

        self.assert_hdreport_report_equal(hdreport_response, report_data2, [self.run2_url], report_url2)

        # Generate a week's worth of report objects
        report_data3 = {'date': '2020-01-04',
                        'resort': self.resort_url,
                        'runs': [self.run3_url, self.run1_url]}
        report_response3 = client.post('/reports/', report_data3, format='json').json()
        report_url3 = 'http://testserver/reports/{}/'.format(report_response3['id'])

        report_data4 = {'date': '2020-01-05',
                        'resort': self.resort_url,
                        'runs': [self.run2_url, self.run1_url]}
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

        # Check that the hdreport for report7 has the expected values
        hdreport_response = client.get(report_response7['hd_report']).json()
        self.assert_hdreport_report_equal(hdreport_response, report_data7, [self.run2_url], report_url7)

        # Adjust one day to include a run2 groom -> run2 no longer under 30% groom rate
        report_response = client.get(report_url6).json()
        report_response['runs'].append(self.run2_url)
        client.put(report_url6, data=json.dumps(report_response), content_type='application/json')
        # TODO: Updating an upstream report does not cause HDReport object to automatically update; must put
        # corresponding report object to get HDReport to update
        client.put(report_url7, data=json.dumps(report_response7), content_type='application/json')
        hdreport_response = client.get(report_response7['hd_report']).json()
        self.assert_hdreport_report_equal(hdreport_response, report_data7, [], report_url7)

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

    def test_report_hdreport_put(self) -> None:
        """
        test report put also updated hdreport object accordingly
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
        hd_report2 = client.get(report_response2['hd_report'], format='json').json()
        self.assert_hdreport_report_equal(hd_report2, report_data2, [self.run2_url],
                                          report_url2)

    def test_get(self) -> None:
        """
        test get method for report
        """
        client = APIClient()
        # Check anon user has GET access
        self.assertEqual(client.get('/reports/').status_code, 200)

        # Check staff user has GET
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        response = client.get('/reports/')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)
        response = response[0]

        response.pop('id')
        response.pop('hd_report')
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
        report_response.pop('hd_report')
        self.assertEqual(report_response, report_data)

    def test_put(self) -> None:
        """
        test put method of report
        """
        client = APIClient()

        report_response = client.get('/reports/1/', format='json').json()
        report_response['runs'] = [self.run1_url]

        # Check anon user has no PUT access
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


class HDReportViewTestCase(TestCase):
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
        cls.resort_data = {'name': 'Beaver Creek', 'location': 'CO', 'report_url': 'foo'}
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

        cls.hdreport_data = {
            'date': '2020-01-01',
            'resort': cls.resort_url,
            'runs': [],
            'full_report': cls.report_url
        }

    def test_get(self) -> None:
        """
        test get method works correctly
        """
        # Check anon user has GET
        client = APIClient()
        self.assertEqual(client.get('/hdreports/').status_code, 200)
        # Check rando user has GET
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.get('/hdreports/').status_code, 200)

        # Check staff GET works as expected
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        response = client.get('/hdreports/')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)
        response = response[0]

        response.pop('id')
        self.assertEqual(response, self.hdreport_data)

    def test_post(self) -> None:
        """
        test post method does not work
        """
        client = APIClient()
        # Check anon user has no POST
        self.assertEqual(client.post('/hdreports/', self.hdreport_data, format='json').status_code, 401)
        # Check rando user has no POSt
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.post('/hdreports/', self.hdreport_data, format='json').status_code, 403)

        # Check staff POSt works as expected
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        response = client.post('/hdreports/', self.hdreport_data, format='json')
        self.assertEqual(response.status_code, 405)

    def test_put(self) -> None:
        """
        test put method
        """
        client = APIClient()

        report_response = client.get('/hdreports/1/', format='json').json()
        report_response['runs'] = [self.run1_url]

        # Check anon user has no PUT
        self.assertEqual(client.put('/hdreports/1/', data=json.dumps(report_response),
                                           content_type='application/json').status_code, 401)
        # Check rando user has no PUT
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.put('/hdreports/1/', data=json.dumps(report_response),
                                    content_type='application/json').status_code, 403)

        # Check staff PUT works as expected
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        run_response_new = client.put('/hdreports/1/', data=json.dumps(report_response),
                                           content_type='application/json')
        self.assertEqual(run_response_new.status_code, 200)
        self.assertDictEqual(run_response_new.json(), report_response)

    def test_delete(self) -> None:
        """
        test delete method does not work
        """
        client = APIClient()
        # Check anon DELETE does not work
        self.assertEqual(client.delete('/hdreports/1/').status_code, 401)
        # Check rando has no DELETE
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.rando_token.key)
        self.assertEqual(client.delete('/hdreports/1/').status_code, 403)

        # Check that staff DELETE works as expected
        client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        report_response = client.delete('/hdreports/1/')
        self.assertEqual(report_response.status_code, 405)

        # Test that deleting report object deletes HDReport object
        self.assertEqual(len(client.get('/hdreports/').json()), 1)
        report_response = client.delete(self.report_url)
        self.assertEqual(report_response.status_code, 204)

        hdreport_response = client.get('/hdreports/')
        self.assertEqual(hdreport_response.status_code, 200)

        hdreport_response = hdreport_response.json()
        self.assertEqual(len(hdreport_response), 0)

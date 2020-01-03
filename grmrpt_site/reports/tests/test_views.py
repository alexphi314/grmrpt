import json
import datetime as dt

from django.test import TestCase
from rest_framework.test import APIClient


class ResortViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()
        cls.resort_data = {'name': 'Beaver Creek', 'location': 'CO', 'report_url': 'foo'}
        resort_response = cls.client.post('/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201

    def test_get(self) -> None:
        """
        Test get returns single resort object
        """

        response = self.client.get('/resorts/', format='json')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)

        # Add id to resort data
        self.resort_data['id'] = 1
        self.assertDictEqual(response[0], self.resort_data)

    def test_post(self) -> None:
        """
        Test post works
        """
        resort_data = {'name': 'Vail', 'location': 'CO', 'report_url': 'bar'}
        response = self.client.post('/resorts/', resort_data, format='json')

        self.assertEqual(response.status_code, 201)

        response = response.json()
        self.assertTrue('id' in response.keys())
        # Remove id from dict -> we care that it was returned but not what it is
        response.pop('id')
        self.assertDictEqual(resort_data, response)

    def test_put(self) -> None:
        """
        Test put method for resorts
        """
        response = self.client.get('/resorts/1/').json()
        response['location'] = 'Kansas'

        update_response = self.client.put('/resorts/1/', data=json.dumps(response), content_type='application/json')
        self.assertEqual(update_response.status_code, 200)
        self.assertDictEqual(update_response.json(), response)

    def test_delete(self) -> None:
        """
        Test delete method for resorts
        """
        resort_data = {'name': 'Vail', 'location': 'CO', 'report_url': 'bar'}
        response = self.client.post('/resorts/', resort_data, format='json')

        id = response.json()['id']
        response = self.client.delete('/resorts/{}/'.format(id))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get('/resorts/{}/'.format(id)).status_code, 404)


class RunViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

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
        response = self.client.get('/runs/')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)
        response = response[0]

        response.pop('id')
        self.assertEqual(response, self.run_data)

    def test_post(self) -> None:
        """
        test post method
        """
        run_data = {'name': 'Cresta', 'resort': self.resort_url,
                    'difficulty': 'black', 'reports': [self.report_url]}
        run_response = self.client.post('/runs/', run_data, format='json')

        self.assertEqual(run_response.status_code, 201)
        run_response = run_response.json()

        run_response.pop('id')
        self.assertEqual(run_response, run_data)

    def test_put(self) -> None:
        """
        test put method
        """
        run_response = self.client.get('/runs/1/', format='json').json()

        report_data = {'date': dt.datetime.strptime('2020-01-01', '%Y-%m-%d').date(),
                       'resort': self.resort_url,
                       'runs': []}
        report_response = self.client.post('/reports/', report_data, format='json')
        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()
        report_url = 'http://testserver/reports/{}/'.format(report_response['id'])

        run_response['reports'].append(report_url)

        run_response_new = self.client.put('/runs/1/', data=json.dumps(run_response),
                                           content_type='application/json')
        self.assertEqual(run_response_new.status_code, 200)
        self.assertDictEqual(run_response_new.json(), run_response)

    def test_delete(self) -> None:
        """
        test delete method
        """
        run_data = {'name': 'Cresta', 'resort': self.resort_url,
                    'difficulty': 'black', 'reports': [self.report_url]}
        run_response = self.client.post('/runs/', run_data, format='json')
        id = run_response.json()['id']

        run_response = self.client.delete('/runs/{}/'.format(id))
        self.assertEqual(run_response.status_code, 204)

        self.assertEqual(self.client.get('/runs/{}/'.format(id)).status_code, 404)


class ReportViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

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

    def test_run_report_link(self) -> None:
        """
        test run objects link back to report after report object created linked to them
        """
        for run_url in [self.run1_url, self.run2_url]:
            run_response = self.client.get(run_url)
            self.assertEqual(run_response.status_code, 200)
            run_response = run_response.json()
            self.assertEqual(len(run_response['reports']), 1)
            self.assertEqual(run_response['reports'][0], self.report_url)

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
        # Check the original hd_report has no runs linked
        hdreport_response = self.client.get('/hdreports/1/', format='json')
        self.assertEqual(hdreport_response.status_code, 200)
        self.assert_hdreport_report_equal(hdreport_response.json(), self.report_data, [],
                                          'http://testserver/reports/1/')

        # Create a second report the day after the original one
        report_data = {'date': '2020-01-02',
                       'resort': self.resort_url,
                       'runs': [self.run1_url]}
        report_response = self.client.post('/reports/', report_data, format='json')
        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()
        report_url = 'http://testserver/reports/{}/'.format(report_response['id'])

        # Check HDreport objects created correctly
        hdreport_response = self.client.get('/hdreports/', format='json')
        self.assertEqual(hdreport_response.status_code, 200)
        hdreport_response = hdreport_response.json()
        self.assertEqual(len(hdreport_response), 2)

        hdreport_response = self.client.get(report_response['hd_report']).json()
        self.assert_hdreport_report_equal(hdreport_response, report_data, [], report_url)

        # Create a third report the day after the original one
        report_data2 = {'date': '2020-01-03',
                       'resort': self.resort_url,
                       'runs': [self.run2_url, self.run1_url]}
        report_response = self.client.post('/reports/', report_data2, format='json')
        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()
        report_url2 = 'http://testserver/reports/{}/'.format(report_response['id'])
        hdreport_response = self.client.get(report_response['hd_report']).json()

        self.assert_hdreport_report_equal(hdreport_response, report_data2, [self.run2_url], report_url2)

        # Delete the posted report
        response = self.client.delete(report_url)
        self.assertEqual(response.status_code, 204)
        response = self.client.delete(report_url2)
        self.assertEqual(response.status_code, 204)

    def test_report_hdreport_put(self) -> None:
        """
        test report put also updated hdreport object accordingly
        """
        # Create a second report the day after the original one
        report_data = {'date': '2020-01-02',
                       'resort': self.resort_url,
                       'runs': [self.run1_url]}
        report_response = self.client.post('/reports/', report_data, format='json').json()
        report_url = 'http://testserver/reports/{}/'.format(report_response['id'])

        # Create a third report the day after the original one
        report_data2 = {'date': '2020-01-03',
                        'resort': self.resort_url,
                        'runs': [self.run2_url, self.run1_url]}
        report_response2 = self.client.post('/reports/', report_data2, format='json').json()
        report_url2 = 'http://testserver/reports/{}/'.format(report_response2['id'])

        # Update the second and third report to include run3
        report_data['runs'].append(self.run3_url)
        report_data2['runs'].append(self.run3_url)

        update_response = self.client.put(report_url, data=json.dumps(report_data),
                                          content_type='application/json')
        self.assertEqual(update_response.status_code, 200)
        update_response2 = self.client.put(report_url2, data=json.dumps(report_data2),
                                           content_type='application/json')
        self.assertEqual(update_response2.status_code, 200)

        # Check updated HDreport objects are right
        hd_report2 = self.client.get(report_response2['hd_report'], format='json').json()
        self.assert_hdreport_report_equal(hd_report2, report_data2, [self.run2_url, self.run3_url],
                                          report_url2)

    def test_get(self) -> None:
        """
        test get method for report
        """
        response = self.client.get('/reports/')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)
        response = response[0]

        response.pop('id')
        response.pop('hd_report')
        self.assertEqual(response, self.report_data)

    def test_post(self) -> None:
        """
        test post method of report
        """
        report_data = {'date': '2019-12-31',
                       'resort': self.resort_url,
                       'runs': [self.run1_url]}
        report_response = self.client.post('/reports/', report_data, format='json')

        self.assertEqual(report_response.status_code, 201)
        report_response = report_response.json()

        # Delete the posted report
        delete_resp = self.client.delete('/reports/{}/'.format(report_response['id']))
        assert delete_resp.status_code == 204

        report_response.pop('id')
        report_response.pop('hd_report')
        self.assertEqual(report_response, report_data)

    def test_put(self) -> None:
        """
        test put method of report
        """
        report_response = self.client.get('/reports/1/', format='json').json()
        report_response['runs'] = [self.run1_url]

        run_response_new = self.client.put('/reports/1/', data=json.dumps(report_response),
                                           content_type='application/json')
        self.assertEqual(run_response_new.status_code, 200)
        self.assertDictEqual(run_response_new.json(), report_response)

    def test_delete(self) -> None:
        """
        test delete method
        """
        report_data = {'date': '2019-12-31',
                       'resort': self.resort_url,
                       'runs': [self.run1_url]}
        report_response = self.client.post('/reports/', report_data, format='json')
        id = report_response.json()['id']

        report_response = self.client.delete('/reports/{}/'.format(id))
        self.assertEqual(report_response.status_code, 204)

        self.assertEqual(self.client.get('/reports/{}/'.format(id)).status_code, 404)


class HDReportViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

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
        response = self.client.get('/hdreports/')
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
        response = self.client.post('/hdreports/', self.hdreport_data, format='json')
        self.assertEqual(response.status_code, 405)

    def test_put(self) -> None:
        """
        test put method
        """
        report_response = self.client.get('/hdreports/1/', format='json').json()
        report_response['runs'] = [self.run1_url]

        run_response_new = self.client.put('/hdreports/1/', data=json.dumps(report_response),
                                           content_type='application/json')
        self.assertEqual(run_response_new.status_code, 200)
        self.assertDictEqual(run_response_new.json(), report_response)

    def test_delete(self) -> None:
        """
        test delete method does not work
        """
        report_response = self.client.delete('/hdreports/1/')
        self.assertEqual(report_response.status_code, 405)

        # Test that deleting report object deletes HDReport object
        self.assertEqual(len(self.client.get('/hdreports/').json()), 1)
        report_response = self.client.delete(self.report_url)
        self.assertEqual(report_response.status_code, 204)

        hdreport_response = self.client.get('/hdreports/')
        self.assertEqual(hdreport_response.status_code, 200)

        hdreport_response = hdreport_response.json()
        self.assertEqual(len(hdreport_response), 0)

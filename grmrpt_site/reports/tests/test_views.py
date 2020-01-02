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
        response.pop('id', None)
        self.assertDictEqual(resort_data, response)

    def test_put(self) -> None:
        """
        Test put method for resorts
        """
        response = self.client.get('/resorts/1').json()
        response['location'] = 'Kansas'

        update_response = self.client.put('/resorts/1', data=json.dumps(response), content_type='application/json')
        self.assertEqual(update_response.status_code, 200)
        self.assertDictEqual(update_response.json(), response)

    def test_delete(self) -> None:
        """
        Test delete method for resorts
        """
        resort_data = {'name': 'Vail', 'location': 'CO', 'report_url': 'bar'}
        response = self.client.post('/resorts/', resort_data, format='json')

        id = response.json()['id']
        response = self.client.delete('/resorts/{}'.format(id))
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get('/restors/{}'.format(id)).status_code, 404)


class RunViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = APIClient()

        cls.resort_data = {'name': 'Beaver Creek', 'location': 'CO', 'report_url': 'foo'}
        resort_response = cls.client.post('/resorts/', cls.resort_data, format='json')
        assert resort_response.status_code == 201
        cls.resort_url = 'http://testserver/resorts/{}'.format(resort_response.json()['id'])

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

        response.pop('id', None)
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

        run_response.pop('id', None)
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

        run_response_new = self.client.put('/runs/1/', data=json.dumps(run_response), content_type='application/json')
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
        cls.resort_url = 'http://testserver/resorts/{}'.format(resort_response.json()['id'])

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

    def test_get(self) -> None:
        """
        test get method for report
        """
        response = self.client.get('/reports/')
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(len(response), 1)
        response = response[0]

        response.pop('id', None)
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

        report_response.pop('id', None)
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

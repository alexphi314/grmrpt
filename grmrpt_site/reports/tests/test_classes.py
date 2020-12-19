from unittest.mock import patch

from django.test import TestCase


class MockTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.patcher = patch('reports.models.publish_sns_topic', autospec=True)
        cls.mock_func = cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

        super().tearDownClass()

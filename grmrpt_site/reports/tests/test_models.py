from unittest.mock import patch, call

from reports.models import *
from .test_classes import MockTestCase


class ResortTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.resort = Resort.objects.create(name='Beaver Creek TEST',
                                           report_url='reports/tests/test_files/dec23.pdf',
                                           location='Avon, CO')
        cls.resort.save()

    def test_str(self) -> None:
        """
        Test __str__ method of model works correctly
        """
        self.assertEqual(str(self.resort), 'Beaver Creek TEST')

    @patch('reports.models.boto3.client', autospec=True)
    def test_sns_topic(self, mock_client):
        mock_sns = mock_client.return_value
        mock_sns.create_topic.return_value = {
            'TopicArn': 'mockarn'
        }
        os.environ['ENVIRON_TYPE'] = 'test'
        os.environ['ACCESS_ID'] = 'foo'
        os.environ['SECRET_ACCESS_KEY'] = 'bar'

        self.patcher.stop()
        resort = Resort.objects.create(name='test 1')
        resort.save()

        resort = Resort.objects.get(id=resort.id)
        self.assertEqual('mockarn', resort.sns_arn)
        mock_sns.create_topic.assert_called_with(Name='test_test_1_bmgrm',
                                                 Attributes={'DisplayName': 'test 1 Blue Moon Grooming Report:'},
                                                 Tags=[{'Key': 'resort', 'Value': 'test 1'}])
        mock_client.assert_called_with('sns', region_name='us-west-2', aws_access_key_id='foo',
                                       aws_secret_access_key='bar')
        resort.sns_arn = None
        resort.save()
        self.patcher.start()

    @patch('reports.models.update_resort_user_subs', autospec=True)
    @patch('reports.models.unsubscribe_user_to_topic', autospec=True)
    @patch('reports.models.boto3.client', autospec=True)
    def test_delete_sns_topic(self, mock_client, mock_unsub, mock_update):
        mock_sns = mock_client.return_value
        resort = Resort.objects.create(name='test1')
        resort.sns_arn = 'mockarn1'
        resort.save()
        os.environ['ACCESS_ID'] = 'foo'
        os.environ['SECRET_ACCESS_KEY'] = 'bar'

        user1 = User.objects.create(username='foo')
        user1.save()
        user2 = User.objects.create(username='bar')
        user2.save()
        resort.bmg_users.set([user1.bmg_user, user2.bmg_user])
        self.assertListEqual([user1.bmg_user, user2.bmg_user], list(resort.bmg_users.all()))

        delete_sns_topic(resort)
        mock_sns.delete_topic.assert_called_with(TopicArn='mockarn1')
        self.assertListEqual([call(user1.bmg_user, mock_sns, resort),
                              call(user2.bmg_user, mock_sns, resort)], mock_unsub.call_args_list)
        mock_client.assert_called_with('sns', region_name='us-west-2', aws_access_key_id='foo',
                                       aws_secret_access_key='bar')

        # Confirm delete_sns_topic called when resort deleted
        mock_sns.reset_mock()
        resort.delete()
        mock_sns.delete_topic.assert_called_with(TopicArn='mockarn1')

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class ReportTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.resort = Resort.objects.create(name='Beaver Creek TEST',
                                           report_url='reports/tests/test_files/dec23.pdf',
                                           location='Avon, CO')
        cls.resort.save()
        cls.report = Report.objects.create(date=dt.datetime.strptime('2019-01-09', '%Y-%m-%d'),
                                           resort=cls.resort)
        cls.report.save()

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


class BMReportTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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


class RunTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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


class BMGUserTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = User.objects.create(username='foo')

    def test_bmg_user_link(self) -> None:
        self.assertEqual(BMGUser.objects.count(), 1)
        bmg_user = BMGUser.objects.all()[0]
        self.assertEqual(bmg_user.user, self.user)
        self.assertEqual(bmg_user.favorite_runs.count(), 0)

    def test_user_token(self):
        self.assertTrue(self.user.auth_token is not None)
        self.assertEqual(1, Token.objects.filter(user=self.user).count())

    def test_phone_regex(self) -> None:
        bmg_user = self.user.bmg_user
        bmg_user.phone = '+13036708900'
        bmg_user.full_clean()

        bmg_user.phone = '+48708790067'
        bmg_user.full_clean()

        bmg_user.phone = '8005764532'
        self.assertRaises(ValidationError, bmg_user.full_clean)

    @patch('reports.models.apply_attr_update', autospec=True)
    @patch('reports.models.subscribe_user_to_topic', autospec=True)
    @patch('reports.models.unsubscribe_arn', autospec=True)
    @patch('reports.models.boto3.client', autospec=True)
    def test_unsubscribe_all(self, mock_client, mock_unsub, mock_sub, mock_attr):
        mock_sns = mock_client.return_value
        mock_sub.return_value = ['mockarn1', 'mockarn2']
        os.environ['ACCESS_ID'] = 'foo'
        os.environ['SECRET_ACCESS_KEY'] = 'bar'
        resort = Resort.objects.create(name='test1')
        resort.sns_arn = 'mockarn1'
        resort.save()
        resort2 = Resort.objects.create(name='test2')
        resort2.sns_arn = 'mockarn2'
        resort2.save()
        user = User(username='foo2')
        user.save()
        user.bmg_user.resorts.set([resort, resort2])

        unsubscribe_all(user.bmg_user)
        mock_client.assert_called_with('sns', region_name='us-west-2', aws_access_key_id='foo',
                                       aws_secret_access_key='bar')
        self.assertListEqual([call(mock_sns, 'mockarn1'), call(mock_sns, 'mockarn2')], mock_unsub.call_args_list)

        # Test called automatically when user deleted
        mock_unsub.reset_mock()
        user.delete()
        self.assertListEqual([call(mock_sns, 'mockarn1'), call(mock_sns, 'mockarn2')], mock_unsub.call_args_list)

    @patch('reports.models.apply_attr_update', autospec=True)
    @patch('reports.models.unsubscribe_user_to_topic', autospec=True)
    @patch('reports.models.subscribe_user_to_topic', autospec=True)
    @patch('reports.models.boto3.client', autospec=True)
    def test_update_resort_user_subs(self, mock_client, mock_sub, mock_unsub, mock_update):
        mock_sns = mock_client.return_value
        resort = Resort.objects.create(name='test1')
        resort.save()
        resort2 = Resort.objects.create(name='test2')
        resort2.save()
        user = User(username='foo2')
        user.save()
        user2 = User(username='foo3')
        user2.save()

        # Add 1 user to the resort
        mock_sub.return_value = ['mockarn1']
        resort.bmg_users.add(user.bmg_user)
        user = User.objects.get(id=user.id)
        mock_client.assert_called_with('sns', region_name='us-west-2', aws_access_key_id='foo',
                                       aws_secret_access_key='bar')
        mock_sub.assert_called_with(user.bmg_user, mock_sns)
        self.assertListEqual(['mockarn1'], json.loads(user.bmg_user.sub_arn))
        self.assertListEqual(['mockarn1'], unpack_json_field(user.bmg_user.sub_arn))

        # Remove 1 user from the resort
        mock_unsub.return_value = []
        resort.bmg_users.remove(user.bmg_user)
        user = User.objects.get(id=user.id)
        mock_unsub.assert_called_with(user.bmg_user, mock_sns, resort)
        self.assertListEqual([], json.loads(user.bmg_user.sub_arn))

        # Add 1 user to the resort
        user.bmg_user.resorts.add(resort)
        user = User.objects.get(id=user.id)
        mock_sub.assert_called_with(user.bmg_user, mock_sns)
        self.assertListEqual(['mockarn1'], json.loads(user.bmg_user.sub_arn))

        # Remove 1 user from the resort
        user.bmg_user.resorts.remove(resort)
        user = User.objects.get(id=user.id)
        mock_unsub.assert_called_with(user.bmg_user, mock_sns, resort)
        self.assertListEqual([], json.loads(user.bmg_user.sub_arn))

        # Add 2 users to the resort
        mock_sub.reset_mock()
        resort.bmg_users.set([user.bmg_user, user2.bmg_user])
        user = User.objects.get(id=user.id)
        user2 = User.objects.get(id=user2.id)
        self.assertListEqual([call(user.bmg_user, mock_sns), call(user2.bmg_user, mock_sns)], mock_sub.call_args_list)
        self.assertListEqual(['mockarn1'], json.loads(user.bmg_user.sub_arn))
        self.assertListEqual(['mockarn1'], json.loads(user2.bmg_user.sub_arn))

        # Remove 2 users from resort
        mock_unsub.reset_mock()
        resort.bmg_users.set([])
        user = User.objects.get(id=user.id)
        user2 = User.objects.get(id=user2.id)
        self.assertListEqual([call(user.bmg_user, mock_sns, resort), call(user2.bmg_user, mock_sns, resort)],
                             mock_unsub.call_args_list)
        self.assertListEqual([], json.loads(user.bmg_user.sub_arn))
        self.assertListEqual([], json.loads(user2.bmg_user.sub_arn))

        # Add 2 users to the resort
        mock_sub.reset_mock()
        user.bmg_user.resorts.add(resort)
        user2.bmg_user.resorts.add(resort)
        user = User.objects.get(id=user.id)
        user2 = User.objects.get(id=user2.id)
        self.assertListEqual([call(user.bmg_user, mock_sns), call(user2.bmg_user, mock_sns)], mock_sub.call_args_list)
        self.assertListEqual(['mockarn1'], json.loads(user.bmg_user.sub_arn))
        self.assertListEqual(['mockarn1'], json.loads(user2.bmg_user.sub_arn))

        # Remove 2 users from the resort
        mock_unsub.reset_mock()
        user.bmg_user.resorts.remove(resort)
        user2.bmg_user.resorts.remove(resort)
        user = User.objects.get(id=user.id)
        user2 = User.objects.get(id=user2.id)
        self.assertListEqual([call(user.bmg_user, mock_sns, resort), call(user2.bmg_user, mock_sns, resort)],
                             mock_unsub.call_args_list)
        self.assertListEqual([], json.loads(user.bmg_user.sub_arn))
        self.assertListEqual([], json.loads(user2.bmg_user.sub_arn))

        # Add 2 resorts to user
        mock_sub.reset_mock()
        mock_sub.return_value = ['mockarn1', 'mockarn2']
        resort.bmg_users.add(user.bmg_user)
        resort2.bmg_users.add(user.bmg_user)
        user = User.objects.get(id=user.id)
        self.assertListEqual([call(user.bmg_user, mock_sns), call(user.bmg_user, mock_sns)], mock_sub.call_args_list)
        self.assertListEqual(['mockarn1', 'mockarn2'], json.loads(user.bmg_user.sub_arn))

        # Remove 2 resorts from user
        mock_unsub.reset_mock()
        resort.bmg_users.remove(user.bmg_user)
        resort2.bmg_users.remove(user.bmg_user)
        user = User.objects.get(id=user.id)
        self.assertListEqual([call(user.bmg_user, mock_sns, resort), call(user.bmg_user, mock_sns, resort2)],
                             mock_unsub.call_args_list)
        self.assertListEqual([], json.loads(user.bmg_user.sub_arn))

        # Add 2 resorts to user
        mock_sub.reset_mock()
        user.bmg_user.resorts.set([resort, resort2])
        user = User.objects.get(id=user.id)
        self.assertListEqual([call(user.bmg_user, mock_sns)], mock_sub.call_args_list)
        self.assertListEqual(['mockarn1', 'mockarn2'], json.loads(user.bmg_user.sub_arn))

        # Remove 2 resorts from user
        mock_unsub.reset_mock()
        user.bmg_user.resorts.set([])
        user = User.objects.get(id=user.id)
        self.assertListEqual([call(user.bmg_user, mock_sns, resort), call(user.bmg_user, mock_sns, resort2)],
                             mock_unsub.call_args_list)
        self.assertListEqual([], json.loads(user.bmg_user.sub_arn))

        # Add 1 user then 1 later. confirm only user 1 is updated
        resort.bmg_users.add(user2.bmg_user)
        mock_sub.reset_mock()
        mock_sub.return_value = ['mockarn1']
        resort.bmg_users.add(user.bmg_user)
        user = User.objects.get(id=user.id)
        mock_sub.assert_called_with(user.bmg_user, mock_sns)
        self.assertListEqual(['mockarn1'], json.loads(user.bmg_user.sub_arn))

        # Remove 1 user
        mock_unsub.reset_mock()
        resort.bmg_users.remove(user.bmg_user)
        user = User.objects.get(id=user.id)
        mock_unsub.assert_called_with(user.bmg_user, mock_sns, resort)
        self.assertListEqual([], json.loads(user.bmg_user.sub_arn))
        self.assertListEqual([user2.bmg_user], list(resort.bmg_users.all()))

        # Repeat same test as above
        mock_sub.reset_mock()
        user.bmg_user.resorts.add(resort)
        user = User.objects.get(id=user.id)
        mock_sub.assert_called_with(user.bmg_user, mock_sns)
        self.assertListEqual(['mockarn1'], json.loads(user.bmg_user.sub_arn))

        mock_unsub.reset_mock()
        user.bmg_user.resorts.remove(resort)
        user = User.objects.get(id=user.id)
        mock_unsub.assert_called_with(user.bmg_user, mock_sns, resort)
        self.assertListEqual([], json.loads(user.bmg_user.sub_arn))
        self.assertListEqual([user2.bmg_user], list(resort.bmg_users.all()))

        # Add 1 resort to user
        user.bmg_user.resorts.add(resort)
        mock_sub.reset_mock()
        mock_sub.return_value = ['mockarn1', 'mockarn2']
        user.bmg_user.resorts.add(resort2)
        user = User.objects.get(id=user.id)
        mock_sub.assert_called_with(user.bmg_user, mock_sns)
        self.assertListEqual(['mockarn1', 'mockarn2'], json.loads(user.bmg_user.sub_arn))

        # Remove 1 resort
        mock_unsub.reset_mock()
        mock_unsub.return_value = ['mockarn1']
        user.bmg_user.resorts.remove(resort2)
        user = User.objects.get(id=user.id)
        mock_unsub.assert_called_with(user.bmg_user, mock_sns, resort2)
        self.assertListEqual(['mockarn1'], json.loads(user.bmg_user.sub_arn))
        self.assertListEqual([resort], list(user.bmg_user.resorts.all()))

        # Perform the same test as above
        mock_sub.reset_mock()
        resort2.bmg_users.add(user.bmg_user)
        user = User.objects.get(id=user.id)
        mock_sub.assert_called_with(user.bmg_user, mock_sns)
        self.assertListEqual(['mockarn1', 'mockarn2'], json.loads(user.bmg_user.sub_arn))

        mock_unsub.reset_mock()
        resort2.bmg_users.remove(user.bmg_user)
        user = User.objects.get(id=user.id)
        mock_unsub.assert_called_with(user.bmg_user, mock_sns, resort2)
        self.assertListEqual(['mockarn1'], json.loads(user.bmg_user.sub_arn))
        self.assertListEqual([resort], list(user.bmg_user.resorts.all()))

    @patch('reports.models.update_resort_user_subs', autospec=True)
    @patch('reports.models.apply_attr_update', autospec=True)
    @patch('reports.models.boto3.client', autospec=True)
    def test_subscribe_user_to_topic(self, mock_client, mock_update, mock_subs_update):
        mock_sns = mock_client.return_value
        self.user.bmg_user.contact_method = 'sms'
        self.user.bmg_user.phone = '3'
        self.user.bmg_user.contact_days = json.dumps(['Mon', 'Tue'])
        self.user.save()
        resort = Resort.objects.create(name='test1')
        resort.sns_arn = 'test1arn'
        resort.save()
        resort2 = Resort.objects.create(name='test2')
        resort2.sns_arn = 'test2arn'
        resort2.save()
        self.user.bmg_user.resorts.set([resort, resort2])
        mock_sns.subscribe.side_effect = [{'SubscriptionArn': 'mockarn1'}, {'SubscriptionArn': 'mockarn2'}]

        sub_arns = subscribe_user_to_topic(self.user.bmg_user, mock_sns)
        self.assertListEqual(['mockarn1', 'mockarn2'], sub_arns)
        self.assertListEqual([call(TopicArn='test1arn', Protocol='sms', ReturnSubscriptionArn=True, Endpoint='3',
                                   Attributes={'FilterPolicy': json.dumps({'day_of_week': ['Mon', 'Tue']})}),
                              call(TopicArn='test2arn', Protocol='sms', ReturnSubscriptionArn=True, Endpoint='3',
                                   Attributes={'FilterPolicy': json.dumps({'day_of_week': ['Mon', 'Tue']})})],
                             mock_sns.subscribe.call_args_list)

        # Set DOW array to empty and change contact method
        self.user.bmg_user.contact_method = 'email'
        self.user.email = 'foobar@gmail.com'
        self.user.bmg_user.contact_days = []
        self.user.save()
        mock_sns.reset_mock()
        mock_sns.subscribe.side_effect = [{'SubscriptionArn': 'mockarn1'}, {'SubscriptionArn': 'mockarn2'}]
        sub_arns = subscribe_user_to_topic(self.user.bmg_user, mock_sns)
        self.assertListEqual(['mockarn1', 'mockarn2'], sub_arns)
        self.assertListEqual([call(TopicArn='test1arn', Protocol='email', ReturnSubscriptionArn=True,
                                   Endpoint='foobar@gmail.com'),
                              call(TopicArn='test2arn', Protocol='email', ReturnSubscriptionArn=True,
                                   Endpoint='foobar@gmail.com')],
                             mock_sns.subscribe.call_args_list)

        # Remove endpoint and assert subscribe not called
        self.user.email = ''
        self.user.save()
        mock_sns.reset_mock()
        subscribe_user_to_topic(self.user.bmg_user, mock_sns)
        self.assertFalse(mock_sns.subscribe.called)

        # Remove resorts and assert subscribe not called
        self.user.email = 'foobar@gmail.com'
        self.user.bmg_user.resorts.set([])
        self.user.save()
        subscribe_user_to_topic(self.user.bmg_user, mock_sns)
        self.assertFalse(mock_sns.subscribe.called)

    @patch('reports.models.boto3.client', autospec=True)
    def test_unsubscribe_arn(self, mock_client):
        mock_sns = mock_client.return_value
        mock_sns.unsubscribe.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        unsubscribe_arn(mock_sns, 'mockarn')
        mock_sns.unsubscribe.assert_called_with(SubscriptionArn='mockarn')

        # Test bad response doesn't cause code to fail
        mock_sns.unsubscribe.return_value = {'bad': 'response'}
        unsubscribe_arn(mock_sns, 'mockarn')
        mock_sns.unsubscribe.assert_called_with(SubscriptionArn='mockarn')

    @patch('reports.models.update_resort_user_subs', autospec=True)
    @patch('reports.models.apply_attr_update', autospec=True)
    @patch('reports.models.unsubscribe_arn', autospec=True)
    @patch('reports.models.boto3.client', autospec=True)
    def test_unsubscribe_user_to_topic(self, mock_client, mock_unsub, mock_apply, mock_update):
        mock_sns = mock_client.return_value
        resort = Resort.objects.create(name='test1')
        resort.sns_arn = 'test1arn'
        resort.save()

        # 1 sub in list
        self.user.bmg_user.sub_arn = json.dumps(['sub1arn'])
        self.user.save()
        mock_sns.get_subscription_attributes.side_effect = [{
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': []}),
                           'Protocol': 'sms', 'TopicArn': 'test1arn'}
        }]
        out = unsubscribe_user_to_topic(self.user.bmg_user, mock_sns, resort)
        self.assertListEqual([call(SubscriptionArn='sub1arn')], mock_sns.get_subscription_attributes.call_args_list)
        mock_unsub.assert_called_with(mock_sns, 'sub1arn')
        self.assertListEqual([], out)

        # 3 subs in list
        self.user.bmg_user.sub_arn = json.dumps(['sub1arn', 'sub2arn', 'sub3arn'])
        self.user.save()
        mock_sns.get_subscription_attributes.reset_mock()
        mock_sns.get_subscription_attributes.side_effect = [{
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': []}),
                           'Protocol': 'sms', 'TopicArn': 'test1arn'}
        }]
        out = unsubscribe_user_to_topic(self.user.bmg_user, mock_sns, resort)
        self.assertListEqual([call(SubscriptionArn='sub1arn')], mock_sns.get_subscription_attributes.call_args_list)
        mock_unsub.assert_called_with(mock_sns, 'sub1arn')
        self.assertListEqual(['sub2arn', 'sub3arn'], out)

        # 2 subs in list, neither matches
        self.user.bmg_user.sub_arn = json.dumps(['sub2arn', 'sub3arn'])
        self.user.save()
        mock_sns.get_subscription_attributes.reset_mock()
        mock_unsub.reset_mock()
        mock_sns.get_subscription_attributes.side_effect = [
            {
                'Attributes': {'FilterPolicy': json.dumps({'day_of_week': []}),
                               'Protocol': 'sms', 'TopicArn': 'test2arn'}
            },
            {
                'Attributes': {'FilterPolicy': json.dumps({'day_of_week': []}),
                               'Protocol': 'sms', 'TopicArn': 'test3arn'}
            }]
        out = unsubscribe_user_to_topic(self.user.bmg_user, mock_sns, resort)
        self.assertListEqual([call(SubscriptionArn='sub2arn'), call(SubscriptionArn='sub3arn')],
                             mock_sns.get_subscription_attributes.call_args_list)
        self.assertFalse(mock_unsub.called)
        self.assertListEqual(['sub2arn', 'sub3arn'], out)

    def test_str(self) -> None:
        self.assertEqual(str(BMGUser.objects.all()[0]), 'foo')

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        super().tearDownClass()


class NotificationTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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


class SNSTopicSubscriptionTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Create 2 resorts
        cls.resort = Resort.objects.create(name='resort1', report_url='foo', location='Vail')
        cls.resort.save()
        cls.resort2 = Resort.objects.create(name='resort2', report_url='foo', location='Avon')
        cls.resort2.save()
        cls.resort3 = Resort.objects.create(name='resort3', report_url='foo', location='Vail')
        cls.resort3.save()
        cls.resort4 = Resort.objects.create(name='resort4', report_url='foo', location='Vail')
        cls.resort4.save()

        # Create 2 users
        cls.user = User.objects.create(username='foo', email='foo@gmail.com')
        cls.user.bmg_user.contact_method = 'sms'
        cls.user.bmg_user.contact_days = json.dumps(['Tue'])
        cls.user.bmg_user.phone = '+18006756833'
        cls.user.bmg_user.save()

        cls.user2 = User.objects.create(username='bar', email='foobar@gmail.com')
        cls.user2.bmg_user.contact_method = 'sms'
        cls.user2.bmg_user.phone = '+18001234567'
        cls.user2.save()

    def test_sns_topic_creation(self) -> None:
        """
        Test sns topics created for each resort
        """
        self.assertListEqual([call(self.resort), call(self.resort2), call(self.resort3), call(self.resort4)],
                             self.mock_func.call_args_list)

    @patch('reports.models.apply_attr_update', autospec=True)
    @patch('reports.models.update_resort_user_subs', autospec=True)
    def test_sns_subscribed(self, mock_subscribe, mock_update) -> None:
        """
        Test user subscription works
        """
        # Link user to resort and resort2
        self.user.bmg_user.resorts.set([self.resort, self.resort2])
        self.user2.bmg_user.resorts.set([self.resort])
        self.user.bmg_user.save()
        self.user2.bmg_user.save()

        self.assertEqual(4, mock_subscribe.call_count)

        # Link user to resort3
        self.user.bmg_user.resorts.add(self.resort3)
        self.assertEqual(6, mock_subscribe.call_count)

        # Remove link to resort2
        self.user.bmg_user.resorts.remove(self.resort2)
        self.user2.bmg_user.resorts.remove(self.resort)
        self.assertEqual(10, mock_subscribe.call_count)

    @patch('reports.models.delete_sns_topic', autospec=True)
    def test_delete_resort(self, mock_delete) -> None:
        """
        test deleting resort removes sns topic
        """
        self.resort4.delete()

        self.assertTrue(mock_delete.called)
        self.assertTrue(mock_delete.assert_called_with, self.resort4)

    @patch('reports.models.apply_attr_update', autospec=True)
    @patch('reports.models.update_resort_user_subs', autospec=True)
    def test_sns_update_reverse(self, mock_subscribe, mock_update) -> None:
        """
        test subscription from reverse side works
        """
        # Link user2 to resort2
        self.resort2.bmg_users.add(self.user2.bmg_user)
        self.assertEqual(2, mock_subscribe.call_count)

    @patch('reports.models.apply_attr_update', autospec=True)
    @patch('reports.models.unsubscribe_arn')
    def test_user_delete(self, mock_unsub, mock_update) -> None:
        """
        test deleting user removes subscription
        """
        usr3 = User.objects.create(username='bas', email='foobar1@gmail.com')
        usr3.bmg_user.contact_method = 'sms'
        usr3.bmg_user.phone = '13037765456'
        usr3.bmg_user.sub_arn = json.dumps(['mock_arn1', 'mock_arn2'])
        usr3.bmg_user.save()
        usr3.delete()
        self.assertListEqual(['mock_arn1', 'mock_arn2'], [item[0][1] for item in mock_unsub.call_args_list])

        # Confirm deleting BMGUser directly also removes sub
        mock_unsub.reset_mock()
        usr3 = User.objects.create(username='basfoo', email='foobar2@gmail.com')
        usr3.bmg_user.contact_method = 'sms'
        usr3.bmg_user.phone = '13037765456'
        usr3.bmg_user.sub_arn = json.dumps(['mock_arn1', 'mock_arn2'])
        usr3.bmg_user.save()
        usr3.bmg_user.delete()
        self.assertListEqual(['mock_arn1', 'mock_arn2'], [item[0][1] for item in mock_unsub.call_args_list])

    @patch('reports.models.update_resort_user_subs', autospec=True)
    @patch('reports.models.unsubscribe_arn', autospec=True)
    @patch('reports.models.boto3.client', autospec=True)
    def test_apply_attr_update(self, mock_client, mock_unsub, mock_update) -> None:
        """
        test updating contact days or contact method causes subscription to update attrs
        """
        mock_sns = mock_client.return_value
        mock_sns.get_subscription_attributes.side_effect = ({
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': []}),
                           'Protocol': 'sms', 'TopicArn': 'mock_topic_arn1'}
        }, {
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': []}),
                           'Protocol': 'sms', 'TopicArn': 'mock_topic_arn2'}
        })

        # Connect user2 to resort1
        self.user2.bmg_user.resorts.add(self.resort)
        self.user2.bmg_user.sub_arn = json.dumps(['mock_arn1', 'mock_arn2'])
        # Add resort2
        self.user2.bmg_user.resorts.add(self.resort2)
        # Update contact days
        self.user2.bmg_user.contact_days = json.dumps(['Tue', 'Wed'])
        self.user2.save()

        # Check filter policy is set correctly
        self.assertListEqual([call(SubscriptionArn='mock_arn1', AttributeName='FilterPolicy',
                                   AttributeValue=json.dumps({'day_of_week': ['Tue', 'Wed']})),
                              call(SubscriptionArn='mock_arn2', AttributeName='FilterPolicy',
                                   AttributeValue=json.dumps({'day_of_week': ['Tue', 'Wed']}))],
                             mock_sns.set_subscription_attributes.call_args_list)

        # Change contact days again
        mock_sns.set_subscription_attributes.reset_mock()
        mock_sns.get_subscription_attributes.side_effect = ({
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': ['Tue', 'Wed']}),
                           'Protocol': 'sms', 'TopicArn': 'mock_topic_arn1'}
        }, {
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': ['Tue', 'Wed']}),
                           'Protocol': 'sms', 'TopicArn': 'mock_topic_arn2'}
        })
        self.user2.bmg_user.contact_days = json.dumps(['Thu'])
        self.user2.save()
        # Check filter policy is set correctly
        self.assertListEqual([call(SubscriptionArn='mock_arn1', AttributeName='FilterPolicy',
                                   AttributeValue=json.dumps({'day_of_week': ['Thu']})),
                              call(SubscriptionArn='mock_arn2', AttributeName='FilterPolicy',
                                   AttributeValue=json.dumps({'day_of_week': ['Thu']}))],
                             mock_sns.set_subscription_attributes.call_args_list)

        # Update contact method
        mock_sns.set_subscription_attributes.reset_mock()
        mock_sns.get_subscription_attributes.side_effect = ({
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': ['Thu']}),
                           'Protocol': 'sms', 'TopicArn': 'mock_topic_arn1'}
        }, {
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': ['Thu']}),
                           'Protocol': 'sms', 'TopicArn': 'mock_topic_arn2'}
        }, {
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': ['Thu']}),
                           'Protocol': 'email', 'TopicArn': 'mock_topic_arn1'}
        }, {
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': ['Thu']}),
                           'Protocol': 'email', 'TopicArn': 'mock_topic_arn2'}
        }, {
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': ['Mon', 'Sun']}),
                           'Protocol': 'sms', 'TopicArn': 'mock_topic_arn1'}
        }, {
            'Attributes': {'FilterPolicy': json.dumps({'day_of_week': ['Mon', 'Sun']}),
                           'Protocol': 'sms', 'TopicArn': 'mock_topic_arn2'}
        })
        mock_sns.subscribe.side_effect = ({'SubscriptionArn': 'mock_arn3'}, {'SubscriptionArn': 'mock_arn4'},
                                          {'SubscriptionArn': 'mock_arn5'}, {'SubscriptionArn': 'mock_arn6'})
        self.user2.bmg_user.contact_method = 'email'
        self.user2.save()

        # Check contact method set
        self.maxDiff = None
        mock_sns.set_subscription_attributes.assert_not_called()
        self.assertListEqual(['mock_arn1', 'mock_arn2'], [item[0][1] for item in mock_unsub.call_args_list])
        self.assertListEqual([call(TopicArn='mock_topic_arn1', Protocol='email', ReturnSubscriptionArn=True,
                                   Endpoint='foobar@gmail.com',
                                   Attributes={'FilterPolicy': json.dumps({'day_of_week': ['Thu']})}),
                              call(TopicArn='mock_topic_arn2', Protocol='email', ReturnSubscriptionArn=True,
                                   Endpoint='foobar@gmail.com',
                                   Attributes={'FilterPolicy': json.dumps({'day_of_week': ['Thu']})})],
                             mock_sns.subscribe.call_args_list)
        self.assertListEqual(['mock_arn3', 'mock_arn4'], unpack_json_field(self.user2.bmg_user.sub_arn))

        # For multiple subscriptions -> change the contact method and contact days
        mock_sns.subscribe.reset_mock()
        mock_unsub.reset_mock()
        mock_sns.set_subscription_attributes.reset_mock()
        self.user2.bmg_user.contact_method = 'sms'
        self.user2.bmg_user.contact_days = json.dumps(['Mon', 'Sun'])
        self.user2.save()

        self.assertFalse(mock_sns.set_subscription_attributes.called)
        self.assertListEqual(['mock_arn3', 'mock_arn4'], [item[0][1] for item in mock_unsub.call_args_list])
        self.assertListEqual([call(TopicArn='mock_topic_arn1', Protocol='sms', ReturnSubscriptionArn=True,
                                   Endpoint='+18001234567',
                                   Attributes={'FilterPolicy': json.dumps({'day_of_week': ['Mon', 'Sun']})}),
                              call(TopicArn='mock_topic_arn2', Protocol='sms', ReturnSubscriptionArn=True,
                                   Endpoint='+18001234567',
                                   Attributes={'FilterPolicy': json.dumps({'day_of_week': ['Mon', 'Sun']})})],
                             mock_sns.subscribe.call_args_list)
        self.assertListEqual(['mock_arn5', 'mock_arn6'], unpack_json_field(self.user2.bmg_user.sub_arn))

        # Clear days of week filter and assert sub not updated
        mock_sns.set_subscription_attributes.reset_mock()
        self.user2.bmg_user.contact_days = json.dumps([])
        self.user2.save()
        self.assertFalse(mock_sns.set_subscription_attributes.called)

    @classmethod
    def tearDownClass(cls):
        # Delete the created resort objects to clean up created SNS topics
        Resort.objects.all().delete()
        User.objects.all().delete()
        super().tearDownClass()


class AlertTestCase(MockTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.resort = Resort.objects.create(name='test1')

        cls.report = Report.objects.create(date=dt.datetime(2020, 2, 1), resort=cls.resort)

        cls.alert = Alert.objects.create(bm_report_id=1)

    def test_str_method(self) -> None:
        """
        test string method works as intended on model
        """
        self.assertEqual(self.alert.sent.strftime('%Y-%m-%dT%H:%M:%S'), str(self.alert))


import json

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from reports.models import Resort


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

        user_data['phone'] = '4'
        user_data['username'] = 'alexphi3'
        user_data['email'] = 'AP_TEST_foo3@gmail.com'
        self.assertEqual(self.client.post(reverse('signup'), data=user_data).status_code, 200)

        user_data['phone'] = '3038776576'
        user_data['username'] = 'alexphi3'
        user_data['email'] = 'AP_TEST_foo4@gmail.com'
        self.assertEqual(self.client.post(reverse('signup'), data=user_data).status_code, 200)

        self.client.force_login(user=usr)
        self.client.get(reverse('profile'))

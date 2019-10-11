from unittest import TestCase, mock
from run import *

from requests.models import Response


class TestSafetyCheck(TestCase):

    def test_package_safety(self):
        packages = [
            "flask==0.10.1",
            "django==1.11.4",
            "jinja2==2.7.3",
            "requests",
            "requests==2.3.0",
            "werkzeug",
            "numpy",
            "keras",
            "colander==0.9.9"
        ]

        safety = [False, False, True, True, False, True, True, True, False]

        for i, package in enumerate(packages):
            vulnerable = vulnerable_requirement(package)
            self.assertIsNone(
                vulnerable) if safety[i] else self.assertIsNotNone(vulnerable)

    @mock.patch('json.loads')
    def test_packaged_checked(self, mock_json):
        mock_json.return_value = None

        packages = [
            "flask==0.10.1",
            "somerandomtest",
            "requests==2.3.0",
            "werkzeug",
        ]

        should_check = [True, False, True, False]

        for package in packages:
            vulnerable_requirement(package)

        self.assertEqual(mock_json.call_count, sum(should_check))

    def test_api_limit_reached(self):
        response = Response
        response.ok = False
        response.headers = {}

        self.assertTrue(api_limit_reached(response))

        response.ok = True
        self.assertFalse(api_limit_reached(response))

        response.headers['X-RateLimit-Remaining'] = 10
        self.assertFalse(api_limit_reached(response))

        response.headers['X-RateLimit-Remaining'] = 1
        self.assertTrue(api_limit_reached(response))

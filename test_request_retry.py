import unittest
from unittest.mock import Mock

import requests

from request_retry import get_with_retries


class RequestRetryTests(unittest.TestCase):
    def test_retries_timeout_then_returns_response(self):
        response = Mock()
        response.raise_for_status.return_value = None
        request_get = Mock(side_effect=[requests.ReadTimeout("slow"), response])
        sleep = Mock()

        result = get_with_retries(
            "https://example.test/data",
            attempts=3,
            backoff_seconds=2,
            request_get=request_get,
            sleep=sleep,
        )

        self.assertIs(result, response)
        self.assertEqual(request_get.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_retries_server_error(self):
        failed = Mock()
        failed.status_code = 503
        failed.raise_for_status.side_effect = requests.HTTPError(response=failed)
        succeeded = Mock()
        succeeded.raise_for_status.return_value = None
        request_get = Mock(side_effect=[failed, succeeded])

        result = get_with_retries(
            "https://example.test/data",
            request_get=request_get,
            sleep=Mock(),
        )

        self.assertIs(result, succeeded)

    def test_does_not_retry_authentication_error(self):
        response = Mock()
        response.status_code = 401
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
        request_get = Mock(return_value=response)

        with self.assertRaises(requests.HTTPError):
            get_with_retries(
                "https://example.test/data",
                request_get=request_get,
                sleep=Mock(),
            )

        request_get.assert_called_once()


if __name__ == "__main__":
    unittest.main()


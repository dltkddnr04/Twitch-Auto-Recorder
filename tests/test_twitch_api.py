import os
import unittest
from unittest.mock import Mock, patch
import requests

from function import twitch_api


class TwitchApiTests(unittest.TestCase):
    def setUp(self):
        twitch_api.headers = None

    def test_helix_configuration_is_optional_for_recording(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TWITCH_CLIENT_ID"):
                twitch_api.get_header_online()

    def test_user_headers_from_environment(self):
        with patch.dict(os.environ, {"TWITCH_CLIENT_ID": "cid", "TWITCH_USER_TOKEN": "token"}, clear=True):
            headers = twitch_api.get_header_online()
        self.assertEqual(headers["Authorization"], "Bearer token")

    def test_followed_channels_use_current_endpoint(self):
        response = Mock()
        response.json.return_value = {
            "data": [{"broadcaster_id": "1", "broadcaster_login": "example"}],
            "pagination": {},
        }
        with patch.object(twitch_api, "_request", return_value=response) as request:
            channels = twitch_api.get_follow_data("2")
        self.assertEqual(channels, [{"to_id": "1", "to_login": "example"}])
        self.assertIn("channels/followed", request.call_args.args[1])

    def test_http_failure_does_not_look_like_offline(self):
        response = Mock(status_code=401)
        response.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
        with patch.object(twitch_api.requests, "request", return_value=response):
            with self.assertRaises(requests.HTTPError):
                twitch_api._request("GET", "https://api.twitch.tv/helix/users")

    def test_request_timeouts_and_retries(self):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        with patch.object(twitch_api.requests, "request", side_effect=[requests.Timeout, response]) as call, \
             patch.object(twitch_api.time, "sleep"):
            self.assertIs(twitch_api._request("GET", "https://example.org"), response)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(call.call_args.kwargs["timeout"], (5, 15))

    def test_cursor_loop_rejected(self):
        response = Mock()
        response.json.return_value = {"data": [], "pagination": {"cursor": "repeat"}}
        with patch.object(twitch_api, "_request", return_value=response), \
             patch.dict(os.environ, {"TWITCH_CLIENT_ID": "cid", "TWITCH_USER_TOKEN": "token"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "repeated"):
                twitch_api.using_pagination("https://api.twitch.tv/helix/channels/followed")


if __name__ == "__main__":
    unittest.main()

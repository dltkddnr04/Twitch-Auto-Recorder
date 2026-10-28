import unittest
from unittest.mock import patch

import tar_cli_multi
import twitch_auto_recorder_cli


class EntryPointTests(unittest.TestCase):
    def test_single_channel_uses_supervisor(self):
        with patch.object(twitch_auto_recorder_cli, "serve", return_value=4) as serve:
            self.assertEqual(twitch_auto_recorder_cli.main(["Channel"]), 4)
        self.assertEqual(serve.call_args.args[0], ["Channel"])
        self.assertEqual(serve.call_args.args[1]("abc"), "https://www.twitch.tv/abc")

    def test_multiple_channels_use_supervisor(self):
        with patch.object(tar_cli_multi, "serve", return_value=0) as serve:
            self.assertEqual(tar_cli_multi.main(["a", "b"]), 0)
        self.assertEqual(serve.call_args.args[0], ["a", "b"])


if __name__ == "__main__":
    unittest.main()

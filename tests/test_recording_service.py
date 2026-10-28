import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import Mock, patch

from function import recording_service as service


def options():
    return {
        "check_interval": 20, "retry_max": 4, "http_timeout": 15,
        "stream_timeout": 90, "segment_timeout": 20, "segment_attempts": 5,
    }


class RecordingServiceTests(unittest.TestCase):
    def test_channel_validation_rejects_paths(self):
        for channel in ["", "../etc", "/tmp", "foo/bar", "a b", "x" * 26, "--help"]:
            with self.subTest(channel=channel), self.assertRaises(ValueError):
                service.validated_channel(channel)
        self.assertEqual(service.validated_channel("Channel_ABC"), "channel_abc")

    def test_environment_validation(self):
        with patch.dict(os.environ, {"CHECK_INTERVAL": "0"}, clear=True):
            with self.assertRaises(ValueError):
                service.load_options()
        with patch.dict(os.environ, {"HTTP_TIMEOUT": "bad"}, clear=True):
            with self.assertRaises(ValueError):
                service.load_options()

    def test_bounded_streamlink_command(self):
        cmd = service.build_command("testchannel", Path("one.capture"), options())
        self.assertIn("https://www.twitch.tv/testchannel", cmd)
        for flag in ("--http-timeout", "--stream-timeout",
                     "--stream-segment-timeout", "--stream-segment-attempts",
                     "--retry-streams", "--retry-max", "--retry-open", "--skip"):
            self.assertIn(flag, cmd)
        self.assertNotIn("--force", cmd)
        self.assertEqual(cmd[-2:], ["--output", "one.capture"])
        self.assertNotIn("gql.twitch.tv", " ".join(cmd))

    def test_detect_ts_and_fragmented_mp4(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "sample.capture"
            file.write_bytes(b"\x47" + b"\x00" * 187 + b"\x47" + b"\x00" * 187)
            self.assertEqual(service.detect_container(file), ".ts")
            file.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"\x00" * 32)
            self.assertEqual(service.detect_container(file), ".mp4")
            file.write_bytes(b"\x01\x02\x03unknown")
            self.assertEqual(service.detect_container(file), ".raw")

    def test_finalize_preserves_real_extension_even_if_ts_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            staging = folder / "2026-01-01-123.capture"
            staging.write_bytes(b"\x00\x00\x00\x18ftypisom")
            messages = []
            worker = service.RecordingWorker("channel", output_root=folder, log=messages.append, options=options())
            self.assertGreater(worker._finalize(staging), 0)
            self.assertTrue((folder / "2026-01-01-123.mp4").exists())
            self.assertFalse(staging.exists())

    def test_empty_capture_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "empty.capture"
            file.touch()
            worker = service.RecordingWorker("channel", output_root=directory, options=options())
            self.assertEqual(worker._finalize(file), 0)
            self.assertFalse(file.exists())

    def test_failed_remux_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            staging = folder / "record.capture"
            staging.write_bytes(b"\x47" + b"\x00" * 187 + b"\x47")
            worker = service.RecordingWorker("channel", output_root=directory, extension="mkv", options=options())
            with patch.object(service.shutil, "which", return_value=None):
                worker._finalize(staging)
            self.assertTrue((folder / "record.ts").exists())
            self.assertFalse((folder / "record.remux.mkv").exists())

    def test_stopped_worker_does_not_remux(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "stream.capture"
            file.write_bytes(b"\x47" + b"\x00" * 187 + b"\x47")
            worker = service.RecordingWorker("channel", directory, "mp4", options=options())
            worker.stop_event.set()
            with patch.object(worker, "_remux") as remux:
                worker._finalize(file)
            remux.assert_not_called()
            self.assertTrue((Path(directory) / "stream.ts").exists())

    def test_missing_streamlink_fails_without_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = service.RecordingWorker("channel", output_root=directory, options=options())
            with patch.object(service.shutil, "which", return_value=None):
                self.assertEqual(worker.run(), 1)

    def test_stop_event_interrupts_process(self):
        process = Mock()
        process.poll.return_value = None
        worker = service.RecordingWorker("channel", options=options())
        worker._set_process(process)
        with patch.object(service, "_signal_process") as signal_mock:
            worker.stop()
            signal_mock.assert_called_once_with(process)
        self.assertTrue(worker.stop_event.is_set())

    @unittest.skipIf(os.name == "nt", "POSIX process group test")
    def test_interrupt_process_group(self):
        proc = Mock(pid=1007)
        proc.poll.return_value = None
        with patch.object(service.os, "killpg") as kill:
            service._signal_process(proc)
        kill.assert_called_once_with(1007, signal.SIGINT)

    def test_launch_error_retries_with_event_driven_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            worker = service.RecordingWorker("channel", output_root=directory, options=options())
            def fail(*args, **kwargs):
                worker.stop_event.set()
                raise PermissionError("blocked")
            with patch.object(service.shutil, "which", return_value="/fake/streamlink"), \
                 patch.object(service.subprocess, "Popen", side_effect=fail):
                self.assertEqual(worker.run(), 0)

    def test_no_ffmpeg_required_for_ts(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "one.capture"
            staging.write_bytes(b"\x47" + b"\x00" * 187 + b"\x47")
            worker = service.RecordingWorker("channel", directory, "ts", options=options())
            with patch.object(service.shutil, "which", return_value=None):
                self.assertGreater(worker._finalize(staging), 0)
            self.assertTrue((Path(directory) / "one.ts").exists())


if __name__ == "__main__":
    unittest.main()

"""Shared, stoppable Twitch recording supervisor for CLI and Qt entry points.

Streamlink owns Twitch authentication, playlist/CDN discovery and segment handling.
We only supervise processes, reconnections, filenames, and optional safe remuxing.
"""

import argparse
from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid

CHANNEL_PATTERN = re.compile(r"^[a-zA-Z0-9_]{1,25}$")
INITIAL_BACKOFF = 10
MAX_BACKOFF = 300
STOP_GRACE_SECONDS = 10


def validated_channel(channel):
    channel = str(channel).strip().lower()
    if not CHANNEL_PATTERN.fullmatch(channel):
        raise ValueError("Twitch channel must be 1-25 letters, numbers, or underscores")
    return channel


def setting(name, default, minimum, maximum):
    try:
        value = int(os.environ.get(name, default))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def load_options():
    return {
        "check_interval": setting("CHECK_INTERVAL", 20, 5, 300),
        "retry_max": setting("RETRY_MAX", 4, 1, 20),
        "http_timeout": setting("HTTP_TIMEOUT", 15, 5, 120),
        "stream_timeout": setting("STREAM_TIMEOUT", 90, 10, 600),
        "segment_timeout": setting("SEGMENT_TIMEOUT", 20, 5, 120),
        "segment_attempts": setting("SEGMENT_ATTEMPTS", 5, 1, 10),
    }


def build_command(channel, destination, options):
    return [
        "streamlink",
        "--http-timeout", str(options["http_timeout"]),
        "--stream-timeout", str(options["stream_timeout"]),
        "--stream-segment-timeout", str(options["segment_timeout"]),
        "--stream-segment-attempts", str(options["segment_attempts"]),
        "--retry-streams", str(options["check_interval"]),
        "--retry-max", str(options["retry_max"]),
        "--retry-open", "3",
        "--skip",
        f"https://www.twitch.tv/{channel}", "best",
        "--output", str(destination),
    ]


def detect_container(path):
    """Determine the *actual* Streamlink output container, not its filename."""
    with path.open("rb") as reader:
        head = reader.read(4096)
    if len(head) >= 8 and head[4:8] in (b"ftyp", b"styp", b"moof"):
        return ".mp4"
    if head and head[0] == 0x47 and (len(head) < 189 or head[188] == 0x47):
        return ".ts"
    return ".raw"


def _signal_process(process):
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGINT)
    except (OSError, ValueError):
        try:
            process.terminate()
        except OSError:
            pass


def _stop_process(process):
    if process.poll() is not None:
        return
    _signal_process(process)
    try:
        process.wait(timeout=STOP_GRACE_SECONDS)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.terminate()
    except OSError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _popen_kwargs():
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _timestamp():
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def _log_stdout(message):
    print(f"[{_timestamp()}] {message}", flush=True)


class RecordingWorker:
    def __init__(self, channel, output_root=None, extension="ts", log=None, options=None):
        self.channel = validated_channel(channel)
        if extension not in ("ts", "mp4", "mkv"):
            raise ValueError("extension must be ts, mp4 or mkv")
        self.extension = extension
        self.output_root = Path(output_root) if output_root is not None else Path.cwd()
        self.options = options if options is not None else load_options()
        self.log = log if log is not None else _log_stdout
        self.stop_event = threading.Event()
        self._lock = threading.Lock()
        self._process = None

    def report(self, message):
        self.log(f"[{self.channel}] {message}")

    def stop(self):
        self.stop_event.set()
        with self._lock:
            process = self._process
        if process is not None:
            _signal_process(process)

    def _set_process(self, process):
        with self._lock:
            self._process = process
        if self.stop_event.is_set():
            _signal_process(process)

    def _clear_process(self, process):
        with self._lock:
            if self._process is process:
                self._process = None

    def _remux(self, source, destination):
        if shutil.which("ffmpeg") is None:
            self.report(f"FFmpeg not installed; preserving original: {source.name}")
            return False
        command = [
            "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
            "-n", "-i", str(source), "-map", "0", "-c", "copy", str(destination),
        ]
        process = None
        try:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       **_popen_kwargs())
            self._set_process(process)
            # Do not leave an orphan remux process on GUI close or Ctrl+C.
            while process.poll() is None:
                if self.stop_event.wait(0.2):
                    _stop_process(process)
                    break
            if process.returncode == 0 and destination.exists() and destination.stat().st_size:
                source.unlink()
                self.report(f"Remux complete: {destination.name}")
                return True
            self.report(f"Remux incomplete; original preserved: {source.name}")
            return False
        except OSError as exc:
            self.report(f"Remux error: {exc}; original preserved")
            return False
        finally:
            if process is not None:
                _stop_process(process)
                self._clear_process(process)
            if destination.exists() and source.exists():
                # A failed remux must not leave a misleading, partial final file.
                try:
                    destination.unlink()
                except OSError:
                    pass

    def _finalize(self, staging_path):
        try:
            if not staging_path.exists():
                return 0
            size = staging_path.stat().st_size
            if not size:
                staging_path.unlink()
                return 0
            suffix = detect_container(staging_path)
            original = staging_path.with_suffix(suffix)
            # Unique UUID output names, no existing-file replacement.
            if original.exists():
                self.report(f"Output collision; preserved temporary file {staging_path}")
                return size
            staging_path.rename(original)
            self.report(f"Saved {original.name} ({size} bytes, format {suffix})")
            if self.extension in ("mp4", "mkv") and not self.stop_event.is_set():
                if suffix != ".raw":
                    # Even MP4 -> MP4 can need timestamp normalization.
                    desired = original.with_name(original.stem + ".remux." + self.extension)
                    self._remux(original, desired)
            elif self.extension != "ts" and self.stop_event.is_set():
                self.report("Stopped: preserved raw capture rather than risk incomplete remux")
            return size
        except OSError as exc:
            self.report(f"Could not finalize capture: {exc} (staging: {staging_path})")
            return 0

    def run(self):
        try:
            self.output_root.joinpath(self.channel).mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.report(f"Unable to create output directory: {exc}")
            return 1
        if shutil.which("streamlink") is None:
            self.report("Streamlink not found; install streamlink>=8.6.2")
            return 1

        self.report("Monitoring with Streamlink Twitch plugin")
        backoff = INITIAL_BACKOFF
        while not self.stop_event.is_set():
            staging = self.output_root / self.channel / f"{_timestamp()}-{uuid.uuid4().hex[:12]}.capture"
            command = build_command(self.channel, staging, self.options)
            started = time.monotonic()
            returncode = None
            process = None
            try:
                process = subprocess.Popen(command, **_popen_kwargs())
                self._set_process(process)
                returncode = process.wait()
            except OSError as exc:
                self.report(f"Streamlink launch error: {exc}")
            finally:
                if process is not None:
                    _stop_process(process)
                    self._clear_process(process)

            elapsed = time.monotonic() - started
            size = self._finalize(staging)
            if self.stop_event.is_set():
                break
            if returncode == 0 and size:
                self.report("Recording ended; resuming monitoring")
            elif size:
                self.report(f"Stream interrupted (exit {returncode}); partial recording preserved")
            else:
                self.report(f"Offline, unavailable or connection failed (exit {returncode})")

            if elapsed >= 60:
                backoff = INITIAL_BACKOFF
            self.report(f"Retrying in {backoff}s")
            self.stop_event.wait(backoff)
            if elapsed < 60:
                backoff = min(MAX_BACKOFF, backoff * 2)

        self.report("Stopped")
        return 0


def run_cli(argv=None):
    parser = argparse.ArgumentParser(description="Resilient Twitch auto recorder")
    parser.add_argument("channels", nargs="+", help="Twitch channel IDs")
    args = parser.parse_args(argv)

    try:
        channels = list(dict.fromkeys(validated_channel(name) for name in args.channels))
        options = load_options()
    except ValueError as exc:
        parser.error(str(exc))

    if shutil.which("streamlink") is None:
        parser.error("Streamlink is missing. Install: python -m pip install -r requirements.txt")
    workers = [RecordingWorker(channel, options=options) for channel in channels]
    threads = [threading.Thread(target=worker.run, name=worker.channel) for worker in workers]
    shutting_down = threading.Event()

    def stop_all(_signum=None, _frame=None):
        shutting_down.set()
        for worker in workers:
            worker.stop()

    signal.signal(signal.SIGINT, stop_all)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop_all)
    for thread in threads:
        thread.start()
    try:
        while not shutting_down.wait(0.5):
            if not any(thread.is_alive() for thread in threads):
                break
    except KeyboardInterrupt:
        stop_all()
    finally:
        stop_all()
        for thread in threads:
            thread.join()
    return 0


if __name__ == "__main__":
    sys.exit(run_cli())

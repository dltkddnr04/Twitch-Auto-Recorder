# Twitch-Auto-Recorder

Twitch broadcast recorder (Python CLI and Streamlink).

## Maintenance policy (2026-10-28)

**CLI ONLY.** The older PyQt GUI (`twitch_auto_recorder.py`), desktop
release executables, related GUI recorder helper, and old API/serverless/clip
experiments are retained solely for historical compatibility and are
**no longer maintained or supported**. No GUI compatibility or release-build
guarantees are made. Current CLI code paths do not require Twitch Helix or the
old serverless token services.

## Installation

Python 3.10+, Streamlink 8.6.2+:

```bash
python -m pip install -r requirements.txt
python twitch_auto_recorder_cli.py CHANNEL_ID
python tar_cli_multi.py CHANNEL_A CHANNEL_B
```

The Twitch platform plugin owns URL/playlist resolution, and auth/CDN handling.
Use the channel's actual Twitch login, not its display name.

The shared CLI supervisor has a bounded startup/stall watchdog, fixed
10-second rechecks (configurable), per-channel worker resurrection, signal
handling, minimum free-space check, unique outputs, abandoned-capture
recovery, and atomic status files (`CHANNEL/.recorder-status.json`).
Both TS and fragmented MP4 inputs can be captured, identified by contents,
and retained without forced remuxing or overwrites. `.raw` outputs require
manual inspection.

See [CLI operations and failure recovery](docs/cli-operations.md) for
configuration, host restart instructions and limitations.

**Important:** existing Windows GUI releases were not rebuilt and do
not contain these CLI changes.

## Verification

```bash
python -m unittest discover -s tests -v
```

MIT License — [LICENSE](LICENSE).

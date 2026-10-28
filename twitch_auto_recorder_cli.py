"""CLI-only Twitch recorder. PyQt GUI is no longer maintained."""
import argparse

from recorder_core import serve


def main(argv=None):
    parser = argparse.ArgumentParser(description="Unattended Twitch CLI recorder")
    parser.add_argument("channel", help="Twitch channel ID")
    args = parser.parse_args(argv)
    return serve([args.channel], lambda channel: f"https://www.twitch.tv/{channel}")


if __name__ == "__main__":
    raise SystemExit(main())

"""Multiple Twitch channels using the same resilient CLI supervisor."""
import argparse

from recorder_core import serve


def main(argv=None):
    parser = argparse.ArgumentParser(description="Unattended multi-channel Twitch recorder")
    parser.add_argument("channels", nargs="+", help="Twitch channel IDs")
    args = parser.parse_args(argv)
    return serve(args.channels, lambda channel: f"https://www.twitch.tv/{channel}")


if __name__ == "__main__":
    raise SystemExit(main())

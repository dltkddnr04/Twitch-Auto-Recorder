"""Multi-channel CLI entry point (shared resilient recorder)."""

from function.recording_service import run_cli


if __name__ == "__main__":
    raise SystemExit(run_cli())

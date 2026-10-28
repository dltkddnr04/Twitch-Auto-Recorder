"""GitHub release metadata; network errors must never block indefinitely."""
import requests

URL = "https://api.github.com/repos/dltkddnr04/Twitch-Auto-Recorder/releases/latest"


def get_release_data():
    response = requests.get(URL, timeout=(5, 10))
    if response.status_code == 404:
        raise ValueError("No published latest release found")
    response.raise_for_status()
    return response.json()


def get_latest_version():
    data = get_release_data()
    return str(data["tag_name"]).lstrip("v")


def get_download_url():
    data = get_release_data()
    assets = data.get("assets", [])
    if not assets:
        raise ValueError("Latest release has no downloadable assets")
    return assets[0]["browser_download_url"]


def get_patch_notes():
    return get_release_data().get("body") or ""


def compare_version(current_version, latest_version):
    def parse(version):
        parts = str(version).lstrip("v").split(".")
        if len(parts) != 3:
            raise ValueError("Unsupported version format")
        return tuple(int(p) for p in parts)
    return parse(latest_version) > parse(current_version)

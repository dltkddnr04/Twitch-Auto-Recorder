"""Twitch Helix API helpers for optional GUI follow-list and clip features.

Recording does not need Helix or an external token proxy.
"""
import os
import time

import requests

BASIC_URL = "https://api.twitch.tv/helix/"
headers = None
TIMEOUT = (5, 15)


def _request(method, url, **kwargs):
    # Timeouts prevent API failures from indefinitely freezing the GUI.
    kwargs.setdefault("timeout", TIMEOUT)
    for attempt in range(3):
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                delay = min(10, max(1, 2 ** attempt))
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def get_access_token(client_id, client_secret):
    response = _request("POST", "https://id.twitch.tv/oauth2/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    })
    return response.json()["access_token"]


def get_header(client_id, access_token):
    global headers
    if not client_id or not access_token:
        raise ValueError("Twitch client ID and OAuth token are required")
    headers = {"Client-ID": client_id, "Authorization": "Bearer " + access_token}
    return dict(headers)


def get_header_online():
    # The old Cloudflare Workers token proxy is no longer a startup
    # dependency. Caller-owned Twitch credentials are required for Helix.
    client_id = os.environ.get("TWITCH_CLIENT_ID", "")
    token = os.environ.get("TWITCH_USER_TOKEN") or os.environ.get("TWITCH_APP_TOKEN", "")
    if not client_id or not token:
        raise RuntimeError(
            "Set TWITCH_CLIENT_ID and TWITCH_USER_TOKEN (user:read:follows) "
            "to import followed channels. Manual recording needs neither."
        )
    return get_header(client_id, token)


def _headers():
    if not headers:
        return get_header_online()
    return headers


def _helix(path, params=None):
    return _request("GET", BASIC_URL + path, headers=_headers(), params=params).json()


def check_user_exists(user_iden):
    if user_iden.isdigit():
        data = _helix("users", {"id": user_iden})
    else:
        data = _helix("users", {"login": user_iden})
    return bool(data.get("data"))


def get_id_from_login(user_login):
    data = _helix("users", {"login": user_login}).get("data", [])
    if not data:
        raise ValueError(f"Unknown Twitch channel: {user_login}")
    return data[0]["id"]


def get_login_from_id(user_id):
    data = _helix("users", {"id": user_id}).get("data", [])
    if not data:
        raise ValueError(f"Unknown Twitch user ID: {user_id}")
    return data[0]["login"]


def get_stream_data(user_id):
    data = _helix("streams", {"user_id": user_id}).get("data", [])
    return data[0] if data else False


def get_clip_data(clip_id):
    data = _helix("clips", {"id": clip_id}).get("data", [])
    if not data:
        raise ValueError(f"Unknown clip ID: {clip_id}")
    return data[0]


def using_pagination(url):
    items = []
    cursor = None
    seen = set()
    for _ in range(1000):
        response = _request("GET", url, headers=_headers(),
                            params={"after": cursor} if cursor else None).json()
        items.extend(response.get("data", []))
        cursor = response.get("pagination", {}).get("cursor")
        if not cursor:
            return items
        if cursor in seen:
            raise RuntimeError("Twitch pagination cursor repeated")
        seen.add(cursor)
    raise RuntimeError("Twitch pagination exceeded safe page limit")


def get_follow_data(user_id):
    # users/follows was removed; channels/followed requires user OAuth with
    # user:read:follows and user_id matching the authorization principal.
    url = BASIC_URL + "channels/followed?user_id=" + str(user_id) + "&first=100"
    items = using_pagination(url)
    return [
        {"to_login": item["broadcaster_login"], "to_id": item["broadcaster_id"]}
        for item in items
    ]


def get_follower_data(user_id):
    url = BASIC_URL + "channels/followers?broadcaster_id=" + str(user_id) + "&first=100"
    return using_pagination(url)


def get_clip_list(user_id, start_time, end_time):
    url = (BASIC_URL + "clips?broadcaster_id=" + str(user_id)
           + "&first=100&started_at=" + str(start_time) + "&ended_at=" + str(end_time))
    return using_pagination(url)


def get_schedule_data(user_id, start_time):
    url = (BASIC_URL + "schedule?broadcaster_id=" + str(user_id)
           + "&started_at=" + str(start_time) + "&first=25")
    return using_pagination(url)


def get_vod_data(user_id, period):
    url = BASIC_URL + "videos?user_id=" + str(user_id) + "&period=" + str(period) + "&first=100&type=archive"
    return using_pagination(url)


def get_chat_from_vod(vod_id):
    raise NotImplementedError(
        "Twitch's historical v5 VOD comments API has been retired; "
        "this feature needs a supported replacement."
    )

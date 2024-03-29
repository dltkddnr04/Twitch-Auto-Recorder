import requests
import json

BASIC_URL = 'https://api.twitch.tv/helix/'

def get_access_token(client_id, client_secret):
    url = 'https://id.twitch.tv/oauth2/token?client_id=' + client_id + '&client_secret=' + client_secret + '&grant_type=client_credentials'
    req = requests.post(url)
    access_token = req.json()['access_token']
    return access_token

def get_header(client_id, access_token):
    global headers
    headers = {'Client-ID': client_id, 'Authorization': 'Bearer ' + access_token}
    return headers

def get_header_online():
    url = "https://get-header.twitch-auto-recorder.workers.dev"
    req = requests.get(url)
    global headers
    headers = json.loads(req.text)
    return headers

def check_user_exists(user_iden):
    if user_iden.isdigit() and len(user_iden) == 9:
        url = BASIC_URL + 'users?id='
    else:
        url = BASIC_URL + 'users?login='

    req = requests.get(url + user_iden, headers=headers)
    json_data = json.loads(req.text)
    if json_data["data"]:
        return True
    else:
        return False

def get_id_from_login(user_login):
    url = BASIC_URL + 'users?login=' + user_login
    req = requests.get(url, headers=headers)
    user_id = req.json()['data'][0]['id']
    return user_id

def get_login_from_id(user_id):
    url = BASIC_URL + 'users?id=' + user_id
    req = requests.get(url, headers=headers)
    user_login = req.json()['data'][0]['login']
    return user_login

def get_stream_data(user_id):
    url = BASIC_URL + 'streams?user_id=' + user_id
    req = requests.get(url, headers=headers)
    json_data = json.loads(req.text)
    try:
        stream_data = json_data["data"][0]
        return stream_data
    except IndexError:
        return False

def get_clip_data(clip_id):
    url = BASIC_URL + 'clips?id=' + clip_id
    req = requests.get(url, headers=headers)
    json_data = json.loads(req.text)
    clip_data = json_data["data"][0]
    return clip_data

def using_pagination(url):
    list = []
    req = requests.get(url, headers=headers)
    json_data = json.loads(req.text)
    list.extend(json_data["data"])
    while json_data["pagination"]:
        next_url = url + '&after=' + json_data["pagination"]["cursor"]
        req = requests.get(next_url, headers=headers)
        json_data = json.loads(req.text)
        list.extend(json_data["data"])
    return list

def get_follow_data(user_id):
    # 이 함수는 유저가 팔로우하는 사람의 목록입니다
    url = BASIC_URL + 'users/follows?from_id=' + user_id + '&first=100'
    follow_data = using_pagination(url)
    return follow_data

def get_follower_data(user_id):
    # 이 함수는 유저를 팔로우하는 사람의 목록입니다
    url = BASIC_URL + 'users/follows?to_id=' + user_id + '&first=100'
    follower_data = using_pagination(url)
    return follower_data

def get_clip_list(user_id, start_time, end_time):
    url = BASIC_URL + 'clips?broadcaster_id=' + user_id + '&first=100&started_at=' + start_time + '&ended_at=' + end_time
    clip_list = using_pagination(url)
    return clip_list

def get_schedule_data(user_id, start_time):
    url = BASIC_URL + 'schedule?broadcaster_id=' + user_id + '&started_at=' + start_time + '&first=25'
    schedule_data = using_pagination(url)
    return schedule_data

def get_vod_data(user_id, period):
    url = BASIC_URL + 'videos?user_id=' + user_id + '&period=' + period + '&first=100&type=archive'
    vod_data = using_pagination(url)
    return vod_data


def get_chat_from_vod(vod_id):
    list = []
    v5_client_id = 'jzkbprff40iqj646a697cyrvl0zt2m6'
    url = 'https://api.twitch.tv/v5/videos/' + vod_id + '/comments'
    req = requests.get(url, params={"client_id": v5_client_id})
    json_data = json.loads(req.text)
    list.extend(json_data["comments"])
    while json_data["_next"]:
        try:
            next_url = url + '?cursor=' + json_data['_next']
            req = requests.get(next_url, params={"client_id": v5_client_id})
            json_data = json.loads(req.text)
            list.extend(json_data["comments"])
            print(json_data["_next"])
        except:
            break
    return list
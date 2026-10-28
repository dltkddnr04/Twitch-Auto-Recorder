# Twitch-Auto-Recorder

Twitch 채널을 자동 녹화하는 Python 프로그램입니다. CLI(단일/다중 채널)와 PyQt5 GUI에서 **같은** Streamlink 기반 녹화 감독 모듈을 사용합니다.

## 설치

Python 3.10 이상 및 Streamlink 8.6.2 이상이 필요합니다.

```bash
python -m pip install -r requirements.txt
```

GUI를 사용하지 않으면 PyQt5는 필수가 아닙니다.

## CLI

```bash
python twitch_auto_recorder_cli.py channel_id
python tar_cli_multi.py first_channel second_channel
```

채널명은 Twitch URL의 영문 채널 ID를 사용합니다. 기존 Twitch Helix API 키 또는 외부 Cloudflare Worker는 **녹화에 필요하지 않습니다**. Streamlink의 Twitch 플러그인이 방송 여부, 인증 토큰, CDN 및 HLS를 처리합니다.

일반적으로 `Ctrl+C`/SIGTERM으로 Streamlink 및 FFmpeg 자식 프로세스도 정리합니다. 방송 중단 및 장애 후 별도 파일을 생성하고 재시도하며, 기존 파일을 덮어쓰지 않습니다.

```bash
python twitch_auto_recorder.py
```

GUI에서는 스트리머 등록·삭제, TS/MP4/MKV 선택 기능을 사용할 수 있습니다. 녹화 원본은 Twitch가 제공한 실제 컨테이너 종류에 따라 `.ts` 또는 `.mp4`(탐지 실패 시 `.raw`)로 저장하며, MP4/MKV 선택 시 FFmpeg가 설치돼 있으면 녹화 종료 후 스트림을 **재인코딩 없이 리먹싱**합니다. 변환이 실패하거나 강제 종료되면 원본을 보존합니다. Twitch의 Enhanced Broadcasting과 광고 구간 때문에 입력이 fragmented MP4일 수 있으며, 확장자 변경만으로 포맷이 변환되지는 않습니다.

### GUI 팔로우 목록 가져오기

Twitch Helix `users/follows` API는 폐기되었습니다. 팔로우 목록을 가져오려면 앱의 `TWITCH_CLIENT_ID`와, 해당 Twitch 사용자에게서 승인받은 `user:read:follows` 범위의 `TWITCH_USER_TOKEN`을 환경변수로 설정해야 합니다. 사용자 ID는 인증된 사용자와 일치해야 합니다. 앱 액세스 토큰만으로는 이 기능을 사용할 수 없습니다. 수동 채널 등록에는 Twitch OAuth가 필요하지 않습니다.

기존 `streamer_list.pickle`/`setup.pickle` 파일은 유지됩니다. 신뢰할 수 없는 pickle 파일은 열지 마세요.

## 장애 복구 설정

| 환경 변수 | 기본값 | 내용 |
| --- | ---: | --- |
| `CHECK_INTERVAL` | 20 | 스트림 탐색 재시도 간격(초) |
| `RETRY_MAX` | 4 | Streamlink 스트림 탐색 재시도 제한 |
| `HTTP_TIMEOUT` | 15 | HTTP 응답 타임아웃(초) |
| `STREAM_TIMEOUT` | 90 | 스트림 입력 대기 타임아웃(초) |
| `SEGMENT_TIMEOUT` | 20 | HLS 세그먼트 요청 대기 타임아웃(초) |
| `SEGMENT_ATTEMPTS` | 5 | 세그먼트 시도 횟수 |

실패가 지속되면 프로세스 재시도 대기시간이 10초부터 최대 300초까지 증가합니다. 60초 이상 지속된 세션 뒤에는 초기화됩니다.

다운로드 저장 위치는 실행한 작업 디렉터리 아래의 `채널아이디/` 디렉터리입니다. 파일명에는 고유한 접미사가 붙어 이전 녹화 내용을 보존합니다.

## 테스트

```bash
python -m unittest discover -s tests -v
```

한계: Twitch 서비스 정책 또는 지역 제한으로 접근이 거부되는 경우 이 프로그램이 그 제한을 우회할 수는 없습니다. 실제 연결 손실로 수신하지 못한 구간을 소급하여 복구하지는 못합니다. 과거의 `function/recorder.py`, `backend/`, `serverless/`, `test/`은 연구용 레거시 코드이며 정상 녹화 실행 경로에서 호출하지 않습니다.

기존 GUI 릴리스 실행 파일은 자동으로 갱신되지 않습니다. 수정된 소스를 사용하거나 새 실행 파일을 빌드해야 합니다.

## License

MIT License. See [LICENSE](LICENSE).

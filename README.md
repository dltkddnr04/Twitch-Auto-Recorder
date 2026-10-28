# Twitch-Auto-Recorder

**유지보수 종료 예정 · CLI 전용.** Twitch GUI 및 자체 Twitch API/CDN 처리는
중단했습니다. 이 프로그램은 [Streamlink](https://streamlink.github.io/)를
실행해 방송을 파일로 저장하는 작은 래퍼입니다. 정교한 아카이빙은
[Integrated Recorder](https://github.com/dltkddnr04/Integrated-Recorder)의 역할입니다.

## 실행

Python 3.10+ 및 Streamlink 8.6.2+:

```sh
python -m pip install -r requirements.txt
python twitch_auto_recorder_cli.py CHANNEL
python tar_cli_multi.py CHANNEL_A CHANNEL_B
```

방송이 오프라인이면 기본 10초마다 다시 조회합니다. Streamlink의 기본 Twitch
플러그인과 `best` 화질을 사용하며, 외부 API 키나 토큰 프록시는 필요하지 않습니다.
`Ctrl+C`/SIGTERM으로 종료합니다. Python 프로세스나 PC 자체가 종료된 경우에는
OS 서비스 관리자(systemd, Windows 작업 스케줄러 등)에서 자동 재시작해야 합니다.

녹화는 현재 작업 디렉터리의 `CHANNEL/` 아래에 저장됩니다.
TS/fMP4는 `.ts`/`.mp4`, 식별하지 못한 데이터는 `.raw`로 보존합니다.
갑작스러운 프로세스 강제 종료 후 남은 `.capture` 파일도 삭제하지 않습니다.
비정상 종료 시 중간까지 받은 파일은 재생되지 않을 수 있으며,
**방송 누락 구간이나 미디어 무결성을 복구·보증하지 않습니다.**

| 환경 변수 | 기본값 | 설명 |
| --- | ---: | --- |
| `CHECK_INTERVAL` | 10 | 오프라인·오류 후 재시도 초 |
| `STARTUP_TIMEOUT` | 120 | 스트림 시작 후 첫 데이터까지 허용할 초 |
| `STALL_TIMEOUT` | 180 | 마지막 파일 증가 후 허용할 초 |
| `HTTP_TIMEOUT` | 15 | Streamlink HTTP 요청 타임아웃 초 |

고급 로깅, 웹 UI, 세그먼트 보관, 독립 watchdog 서비스는 의도적으로 지원하지 않습니다.
무인 운영 시 표준 출력·오류 로그를 보존하고 OS 서비스 관리자를 사용하세요.

테스트: `python -m unittest discover -s tests -v`

MIT License. [LICENSE](LICENSE)

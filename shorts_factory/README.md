# 숏츠 공장

대본(JSON) → AI 음성 + 자막 + 배경 → 1080x1920, 59초 이하 MP4 → 유튜브 업로드 → 성과 → AI 피드백(무료 AI 우선 자동) → 새 대본 (반복)

## 설치 (1회)
```
pip install edge-tts google-api-python-client google-auth-oauthlib   # + ffmpeg 필요
```

## 사용
| 할 일 | 명령 |
|---|---|
| 영상 1개 만들기 | `python make_short.py scripts/001.json` |
| AI로 새 대본 5개 | `python feedback.py --n 5` (아무 AI 키 1개) |
| 업로드 | `python upload.py out/001.mp4` |
| 전체 자동(하루 1회) | `./factory.sh` |

## 배경 영상
`assets/clips/*.mp4` 에 **본인이 만든 AI 영상**(Runway·Kling·Sora 등 유료 플랜 = 상업 이용 가능) 또는
Pexels/Pixabay 무료 영상을 넣으면 자동 사용. 없으면 그라데이션.
배경음악은 `assets/music.mp3` (유튜브 오디오 보관함 무료 곡 추천).

## ⚠️ 수익화 규칙 (어기면 수익 정지)
- 남의 인스타/유튜브 영상 그대로 재업로드 = 저작권 위반 + "재사용 콘텐츠"로 수익화 거절
- 트렌드는 **주제/형식만** 참고하고 영상은 직접 생성
- AI 합성 표시(`containsSyntheticMedia`)는 업로드 시 자동 ON
- 수익 조건: 구독자 1,000 + 숏츠 조회 90일 1,000만 (1차 단계: 구독 500 + 조회 300만 → 팬후원 기능만)

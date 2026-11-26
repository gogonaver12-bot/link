# PC 렌더 쇼츠 (호러 3D · AI 뉴스)

폰 앱(영상제작 → 🖥 PC 렌더 쇼츠)이나 `python -m mother local plan horror "브리프"`로 대본을 만들면 `jarvis/local_jobs.json`에 대기열이 생겨요.
이 PC에서 `run_local_jobs.bat`을 더블클릭하면 대기열을 렌더해서 폰 앱 '방금 만든 영상'으로 보내요.

- 렌더 엔진: JARVIS-VIDEO-FACTORY `feat/video-unified-20261107` 브랜치(쇼츠 v2~v4, Blender 3D, 호러, AI 뉴스) 작업 폴더
- 처음 실행 때 경로(작업 폴더·assets·Supertonic 3 모델·TTS 파이썬)를 물어보고 `local_config.json`에 저장(저장소에 안 올라감)
- 결과는 720p·4.5Mbps로 줄여 폰 전송 한도(30MB) 안으로. `local_config.json`에서 `"glitch": true`면 장면 전환 RGB 글리치
- 자동 예약(30분마다): `schtasks /create /tn link-local-shorts /sc minute /mo 30 /tr "\"%CD%\run_local_jobs.bat\" auto"`

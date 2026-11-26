---
name: local-shorts-factory
description: "Use when the user wants a horror 3D or AI news short rendered with the PC video factory (Supertonic TTS, Blender) instead of the cloud pipeline"
---
<!-- 자동 생성: skills/local-shorts-factory.md 에서 (mother hub sync) -->
# PC 렌더 쇼츠 (영상 공장 연동)

## 개요
대본(plan JSON)은 클라우드에서 만들고 영상 공장 규칙으로 검사, 렌더는 사용자 PC에서만 한다(TTS 모델·폰트·Codex 로그인이 PC에만 있음).

## 절차
1. `python -m mother local plan horror "브리프"` 또는 `local plan ainews "주제"` (앱: 영상제작 → 🖥 PC 렌더 쇼츠)
2. 규칙: 이야기 1개, 장면 5개, ko 1~48자(한글), en 5~22 ASCII 단어, key는 ko의 부분 문자열, tag 1~16자, hook 1~2줄×8자, 뉴스는 `source: 출처: …` 필수·공개 출처 사실만
3. PC: `tools/local_runner/run_local_jobs.bat` → `python -m jarvis.shorts_horror3d|shorts_ainews --assets … --ko-model … --tts-python … --output … --plan …`
4. 결과를 720p·4.5Mbps(30MB 이하)로 줄여 `app/previews/local-*.mp4`로 올림 → 폰 앱 '방금 만든 영상'

## 흔한 실수
- 클라우드에서 렌더를 시도함(모델이 없어 실패) — 렌더는 PC만
- 비밀키·로그인 정보를 커밋 — `local_config.json`은 경로만, 저장소에 안 올라감
- 뉴스 대본에 확인 안 된 사실을 넣음

## 끝났는지 확인
`python -m mother local list`에서 상태가 done이고, 앱 영상확인에 영상이 보이면 완료.

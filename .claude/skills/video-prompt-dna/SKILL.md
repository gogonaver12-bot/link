---
name: video-prompt-dna
description: "영상 장면 프롬프트 규칙 (AI 영상·배경 생성용)"
---
<!-- 자동 생성: skills/video_prompt_dna.md 에서 (mother hub sync) -->
<!-- source: jarvis-video-factory/jarvis/prompt_dna.py (공개 가이드 재작성본) -->
<!-- source: jarvis-video-factory/jarvis/prompt_dna.py (공개 가이드 재작성본) -->
# 영상 장면 프롬프트 규칙 (AI 영상·배경 생성용)

## ⭐ 시네마틱 프롬프트 5단계 황금 공식 (사장님 지정 · 최우선)
영문으로, 아래 순서 그대로 한 문단: **[1 샷 크기·카메라 무빙] + [2 피사체·구체적 동작] + [3 배경·질감] + [4 조명·색감] + [5 카메라·렌즈 스펙]**
코드: `mother/cinematic.py` (`compose`·`lens`·`clean`) — 스토리 이미지·Flow/Veo 프롬프트에 자동 적용.

| 요소 | 팁 | 키워드 예 |
|---|---|---|
| 1 샷·무빙 (가장 중요) | 카메라 위치·움직임 명확히 | Medium close-up, Low-angle tracking shot, Slow dolly in, FPV drone shot, Handheld camera |
| 2 피사체·동작 | 외형 + 물리적 움직임을 동사로 | beads of sweat dripping, fabric fluttering in the wind, subtle facial expression, turning head slowly |
| 3 배경·질감 | 공간 깊이 + 표면 질감 | wet asphalt reflecting neon lights, dust particles floating in the air, weathered concrete, lush misty forest |
| 4 조명·색감 | 빛 방향·시간대·색보정 | Golden hour backlighting, volumetric god rays, chiaroscuro lighting, teal and orange color grading |
| 5 카메라 스펙 | 실제 시네마 카메라·렌즈 | Shot on ARRI Alexa 65, 35mm anamorphic lens, shallow depth of field, natural film grain, f/1.4 bokeh |

샷별 렌즈: 클로즈업 → ARRI Alexa 65·85mm prime·hyper-realistic skin texture / 액션·트래킹 → RED V-Raptor·24mm·high shutter speed /
제품 매크로 → Phantom Flex4K·100mm macro·rim lighting / 항공·풍경 → DJI Inspire 3·24mm·high dynamic range.

예시(인물 클로즈업): Extreme close-up, slow dolly in on a weathered fisherman in his 50s standing on a boat deck during a storm. Raindrops
hitting his face, wet beard, intense gaze toward the horizon. Dramatic overcast sky, cold blue and moody lighting, water spray in the air.
Shot on ARRI Alexa, 85mm prime lens, shallow depth of field, hyper-realistic skin texture, natural 35mm film grain.

**흔한 실수 3가지 (금지)**
1. 추상 형용사(beautiful, awesome, masterpiece, ultra 8k) → 과장된 CG 느낌. 대신 빛 방향·렌즈 화각·표면 질감.
2. 5~8초 클립에 동작 3개 이상 → 물리 법칙 깨짐. **동작 1개만.**
3. 카메라 무빙 없음 → 정지 사진처럼 어색. 최소 slow push in 이나 subtle handheld movement.

```
JARVIS VIDEO PROMPT DNA v1

For every shot:
1. SUBJECT: name one dominant subject and the visual attribute needed to identify it.
2. MOTION: describe visible physical action, preferably in chronological order.
3. SCENE: state a concrete environment, time/context, and important moving background element.
4. SHOT/SPATIAL: state shot size plus foreground/midground/background or subject position.
5. CAMERA: choose one main camera behavior (push-in, pull-out, pan, tilt, tracking, orbit, locked-off).
6. LIGHT: specify direction/quality of light and keep one coherent palette across adjacent shots.
7. ATMOSPHERE: describe the emotional visual result with concrete cinematic cues.
8. CONTINUITY: preserve subject identity, direction of movement, palette and screen geography between adjacent shots.

Rules:
- Prefer one primary action per shot.
- Write events in the order they happen.
- Describe motion, not vague adjectives.
- Avoid generic filler such as 'amazing', 'best quality', or keyword spam.
- Do not combine contradictory camera instructions.
- The first shot must be understandable without narration and create curiosity within one second.
- Every shot must visually support the narration beat assigned to it.
- Prefer source footage or generated imagery with strong subject separation and room for captions.
- Avoid repeated framing, repeated source clips, excessive digital zoom, and slideshow-like stillness.
- Keep captions as overlays, not as part of scene depth.
```

출처:
- Tencent HunyuanVideo 1.5 Prompt Handbook:
  https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/assets/HunyuanVideo_1_5_Prompt_Handbook_EN.md
- OpenMontage universal video prompting guide:
  https://github.com/calesthio/OpenMontage/blob/main/skills/creative/video-gen-prompting.md
- LTX video prompt cookbook (MIT):
  https://github.com/quanluo/ltx-video-prompts

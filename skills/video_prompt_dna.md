<!-- source: jarvis-video-factory/jarvis/prompt_dna.py (공개 가이드 재작성본) -->
# 영상 장면 프롬프트 규칙 (AI 영상·배경 생성용)

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

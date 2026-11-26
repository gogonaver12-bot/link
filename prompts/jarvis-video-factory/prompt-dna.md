<!-- source: gogonaver12-bot/jarvis-video-factory docs/PROMPT_DNA.md (사용자 승인으로 공개 통합, 2026-11-26) -->
# JARVIS Production Prompt DNA

This project uses a **derived prompt framework**, not copied example prompts.

Sources reviewed:
- Tencent HunyuanVideo 1.5 Prompt Handbook  
  https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/blob/main/assets/HunyuanVideo_1_5_Prompt_Handbook_EN.md
- OpenMontage Universal Video Generation Prompting  
  https://github.com/calesthio/OpenMontage/blob/main/skills/creative/video-gen-prompting.md
- LTX Video Prompt Cookbook (MIT)  
  https://github.com/quanluo/ltx-video-prompts

## JARVIS shot formula

**Subject → concrete motion → scene → shot/spatial staging → one camera behavior → lighting/palette → atmosphere → continuity**

Additional production rules:
- one dominant visual idea per shot
- chronological physical action rather than abstract adjectives
- explicit camera language
- consistent palette across adjacent shots
- narration-to-screen semantic match
- first-second hook that works even muted
- no repeated source shot unless it changes story meaning
- captions treated as overlays and kept inside safe zones

The implementation lives in `jarvis/prompt_dna.py` and is injected into the story/shot planning prompt.

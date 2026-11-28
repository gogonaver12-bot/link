---
name: ai-drama-pipeline
description: Use when producing an episodic AI live-action short drama (consistent characters across episodes, speaking characters with lip sync, no subtitles) from a one-line logline
---
# AI Live-Action Short Drama Pipeline

One logline → a series bible → per-episode 9:16 shorts where the *same* faces keep appearing and characters actually speak. Built for free-first tooling with a paid upgrade path (Veo / Google Flow).

## When to use
- Story/drama Shorts channels ("girl pulls the sword", SCP interviews, rom-com, horror)
- You need character consistency across episodes without training a model
- You want characters talking on screen instead of subtitles + narration

## Steps
1. **Series bible (JSON)** — title, genre, logline, tone, visual `setting` (English), 2–4 characters `{id, name, role, voice: female|girl|male|boy|old_male|old_female, look: concrete English description}`, 5-episode arc. Original characters only (no existing IP); public-domain myths are fine; SCP needs CC BY-SA attribution.
2. **Reference photos once per series** — per character: a full-body reference sheet and a *dialogue portrait* (medium close-up, facing camera, mouth visible, in the series setting). Fixed seed per character. Every later shot passes these as reference images → same face every episode.
3. **Episode script** — 8–11 scenes `{speaker: narrator|character_id, line: ~18 chars, shot: English shot with [character_id] placeholders, camera, light, emotion}`; ≤50 s total; hook in 3 s; cliffhanger last. Expand `[id]` to the character's `look` text when prompting.
4. **Voices first** — TTS each line with per-character voice (pitch/rate offsets distinguish girl/old man/etc.). Keep these exact files: they drive lip sync *and* the final mix, so mouths stay in sync.
5. **Scene media priority**
   - Uploaded clip from Google Flow / Gemini app (Ingredients = character photos; prompt contains the Korean/English line in quotes → the character speaks it). Use the clip's own audio, trimmed at the trailing silence.
   - Veo API (billing): image + prompt with the spoken line; trim at speech end.
   - Free: speech-to-video (Wan2.2-S2V) from dialogue portrait + line audio → lip-sync on a motion clip (LatentSync) → talking head (EchoMimic).
   - Narration/action scenes: image-to-video (Wan2.2 fast / LTX) or Ken Burns.
   Cap every free Space call (≈4–5 min) and the whole run (≈20 min) so CI never hits its job timeout.
6. **Assemble without subtitles** — talking clips are never time-stretched (lips break); motion clips may stretch ≤2×; cinematic grade (contrast, vignette, grain) and 0.18 s fades; voice track concatenated with no gaps.
7. **Upload** to a *separate* drama channel token; private until that channel is connected; episodes in order (ep1 first).

## Common mistakes
- Using each scene image as the talking reference → faces drift between episodes (use the dialogue portrait)
- Letting the model write "English:" prefixes or `...` into JSON → sanitize and use JSON mode on retry
- Waiting forever on shared GPU queues → per-call and per-run time budgets

## Verify
Episode log shows `talking clips ≥ 1`, characters match across two episodes side by side, and the final video has no caption track.

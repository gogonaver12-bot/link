---
name: shorts-autopilot
description: Use when building or running a fully automated faceless YouTube Shorts pipeline (script → hook check → voice → visuals → captions → music ducking → upload → stats feedback) with free tools and GitHub Actions
---
# Shorts Autopilot

Turn one topic (or none) into a published 9:16 Short every day, then let view data steer the next script. Built and run in production on GitHub Actions with free AI providers; works in any language (examples are Korean/English).

## When to use
- You want a daily faceless Shorts channel with zero manual editing
- You have free/cheap keys only (Gemini, Groq, Edge TTS, Pexels/Pixabay, YouTube OAuth)
- You need the agent to *improve* scripts from real channel stats, not guess

## Pipeline (do these in order)
1. **Benchmark first** — search recent Shorts in your niche (YouTube Data API `search.list` + `videos.list`), keep ≤70 s, compute `views/day` and `views ÷ channel subscribers`. Treat ratio ≥ 3 as an outlier worth copying *structurally* (never copy content).
2. **Script JSON** — `{title, hook, lines[6–9], cta, description, tags, keywords[one English stock query per line], visual_hook}`. Rule: lines ≈ target_seconds ÷ 3, order = hook → twist/core → evidence → call to action, one idea per line (~15 chars KO / ~8 words EN).
3. **Hook gate** — score the first line (specificity, direct address, loss/stake, curiosity gap, brevity). Below threshold → ask the model to rewrite *against the weakest dimension* up to 3 rounds; keep the best. Never publish a hook that fails twice.
4. **Cover copy** — generate 5 two-line overlays, reject template leftovers ("N things", "N×"), allow only one number, pick by a title checker.
5. **Voice** — Edge TTS per line (`rate +10%`), concatenate *without gaps* so caption cues = audio cues exactly; loudnorm −14 LUFS.
6. **Visuals per line** — try AI image (Gemini → free FLUX endpoint) → stock video (Pexels/Pixabay) → gradient. Images get Ken Burns with alternating moves (zoom-in, zoom-out, pan L→R, R→L) + lanczos upscale + light unsharp.
7. **Captions** — ASS subtitles, one cue per line, title/cover pinned at top.
8. **Sound** — BGM ducked under the voice with `sidechaincompress`, SFX: whoosh at 0 s, pop on every cut, ding at the end; `alimiter` at 0.95.
9. **Upload** — YouTube Data API with an OAuth *refresh token* stored as a CI secret (API keys cannot upload). Set `containsSyntheticMedia: true`; set `selfDeclaredMadeForKids` honestly. Handle `uploadLimitExceeded` by keeping the item queued for tomorrow.
10. **Feedback loop** — next day pull `statistics` for every upload; feed best/worst titles + benchmark brief into the next script prompt.

## Common mistakes
- Uploading with an API key (fails) or committing tokens (use CI secrets only)
- 0.08 s gaps between TTS lines → captions drift ~1 s by the end
- Marking a script "done" before the upload URL actually came back
- Re-rendering the oldest backlog first — always produce the newest (freshest-feedback) script first
- Mass-producing near-identical videos (YouTube demonetizes repetitive/inauthentic content) — 1–2 per day, varied topics

## Verify it worked
The run log ends with a `youtube.com/shorts/<id>` URL, the next run's stats pull includes that id, and the hook score of the published line is ≥ your threshold.

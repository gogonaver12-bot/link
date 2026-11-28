---
name: hook-scorer
description: Use when writing or judging the first line of a Short, Reel, TikTok, ad or post — score the hook on five dimensions without an LLM, then rewrite against the weakest one
---
# Hook Scorer (zero-token)

A deterministic hook check you can run thousands of times for free, plus a rewrite loop that targets the weakest dimension.

## Dimensions (0–100 each)
- **Specificity** — numbers, names, quoted words, concrete nouns (+); vague words like "amazing/secret/things" (−)
- **Direct address** — "you / your" early (first 6 words) scores most
- **Stake / loss** — what the viewer loses or risks by scrolling away
- **Curiosity gap** — open question or unresolved claim; closed statements lose points
- **Brevity** — sweet spot ≈ 6–14 words (≈ 12–28 Korean chars)

Verdict = 0.6 × average + 0.4 × minimum (a single weak dimension drags the hook down). Bands: ≥72 strong, 55–71 usable, <55 weak.

## Procedure
1. Score the hook. If verdict < threshold (50 for daily automation, 70 for paid ads):
2. Tell the model the weakest dimension and its fix rule (e.g., "add one concrete number or name", "address the viewer in the first 3 words", "end on an unanswered question").
3. Generate 5 candidates, score all locally, keep the best; up to 3 rounds.
4. Never publish a hook that is still < threshold after 3 rounds — skip the script.

## Cover / title check
Length ≤ 60 chars for titles; overlay 2–3 lines ≤ 12 chars each; exactly one number; reject leftover template words ("N things", "N×"); avoid unverifiable multipliers ("2× smarter").

## Common mistakes
- Optimizing the average while one dimension is near zero
- Clickbait that the video does not pay off (hurts retention more than a weak hook)

## Verify
Published hooks show their score and weakest dimension in the run log; the score is ≥ threshold.

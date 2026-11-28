---
name: idea-survival-test
description: Use when deciding whether a business idea or automation pipeline is worth running — research evidence, let competing AI models estimate, Monte Carlo simulate 90-day profit, and auto-improve ideas that fail
---
# Idea Survival Test

"Only survivors get resources." A repeatable gate that turns gut-feel ideas into a pass/fail with numbers, then tries to rescue the failures before killing them.

## When to use
- Before spending money/time on a side business, product, or content pipeline
- Weekly re-check of everything that is running (kill what no longer survives)

## Procedure
1. **Research** — search the web for competing products: price points, review counts (sales proxy), search demand, known failure cases. Keep numbers + URLs, ≤10 lines.
2. **Competing estimators (≥2 different model vendors)** — personas *neutral*, *bear*, *bull*. Each returns JSON: `price_usd, conv_rate_pct (100 = ad model), visitors_low, visitors_high, ramp_days, setup_cost_usd, unit_cost_pct, monthly_cost_usd, competition: low|mid|high, risks[], evidence[]`. If fewer than two models answered → verdict **HOLD**, not pass/fail.
3. **Aggregate** — median of each number; disagreement = max |log(high_i / median)|; widen uncertainty by it.
4. **Monte Carlo (2,000 runs, 90 days)** — steady traffic ~ log-uniform(low, high) × competition factor (low 1.15 / mid 0.85 / high 0.55) × lognormal noise; conversion with lognormal noise (σ = 0.5 + disagreement); ramp ~ ramp_days × U(0.7, 1.6); Poisson sales per day; costs = setup + unit % + monthly/30 per day.
5. **Verdict** — pass if P(profit) ≥ 40 % **and** median ROI ≥ +30 %. Report P10/P50/P90 revenue and break-even day.
6. **Diagnose → improve → retest (max 2 rounds)** — name the numeric failure (price too low, conversion < 1 %, traffic < 100/day, costs > revenue, high competition, ramp > 45 days, models disagree). Ask a model for ONE fix that changes those numbers (pricing/bundle/B2B, market/language, platform, cost). Retest; adopt only if strictly better (never adopt a HOLD); kill if still failing and log the lesson.
7. **Calibrate** — after 30 real days compare each model's revenue estimate with actuals and score the models; trust the accurate ones more.

## Common mistakes
- One model answering = no competition (garbage-in confidence)
- Letting the optimistic persona's numbers through unchallenged
- Killing without trying a numeric fix, or "fixing" by only changing the name

## Verify
Output contains the 3 estimates with model names, the simulation numbers, the verdict, and (if failed) the diagnosis + attempted fixes.

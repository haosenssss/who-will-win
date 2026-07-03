---
name: football-predictor
description: >
  Football (soccer) match prediction and betting-odds value analysis with deep
  web research and a Dixon-Coles probability engine. Use whenever the user asks
  who will win a football match, wants a match preview, prediction, or analysis
  (1X2 win/draw/loss, Asian handicap, China Sports Lottery 让球, exact score),
  shares a screenshot or text of betting odds to evaluate, or asks for a
  betting plan or parlay across matches — even if they don't say "predict".
  Triggers include: 足球预测, 比赛分析, 胜平负, 让球, 亚盘, 水位, 竞彩, 串关,
  比分预测, 赔率, odds analysis, handicap, accumulator, parlay, "Arsenal vs
  Liverpool who wins". Football only — not other sports, not financial advice.
compatibility: Needs web search + a Python 3.8+ runtime for bundled scripts (stdlib only).
---

# Football Predictor

Predict football match outcomes — 1X2, Asian handicap, CSL 让球胜平负, exact
scores — through large-scale web research compressed into calibrated expected
goals, then priced by deterministic scripts. One pipeline regardless of input:
a fixture, a fixture plus an odds screenshot, or several fixtures for a parlay.

Respond in the language the user asked in. All repo docs are EN/中文; that is
for maintainers, not a constraint on your replies.

## Pipeline

1. **Fixture lock.** Confirm match, competition, date, venue, leg. Ambiguity
   (cup vs league same week) → ask the user. Wrong fixture = unfixable.
2. **Research.** Read `references/analysis-framework.md` and run its search
   playbook. This is the product — do it in full:
   - Phase 1: team-level batch (8–10 parallel searches)
   - Phase 2: **per-player sweep — one sub-agent per team** (Agent tool where
     available), each returning a structured availability table
   - Phase 3: track-record deep-read — last-5 match reports, H2H process,
     tournament pedigree, coach style search (can be a third sub-agent)
   - Phase 4: gap fill (xG, rest differential, weather, referee)
   Classify every source by tier (§6 of the framework). Only Tier 1/2 sources
   justify parameter adjustments; prediction articles and expert picks are
   sentiment, nothing more.
3. **Derive λs** per `references/quantification.md` (8 bounded steps). Write
   the preliminary λs down **before** looking at any odds.
4. **Source odds** per `references/odds-sourcing.md`: screenshot → transcribe
   all, echo back if any cell is uncertain; no screenshot → best-effort web
   fetch with source+timestamp; nothing found → fair-odds-only report.
5. **Compute.** Never do market math in prose:
   ```
   python3 scripts/predict.py --home-lambda 1.55 --away-lambda 1.00 \
     --style-home controlled --home-name X --away-name Y --format json > out.json
   ```
6. **Calibrate** (framework Layer 3): model vs no-vig market; >10pp gap on any
   outcome → re-examine, and keep the divergence only with a written "why the
   market is wrong" thesis. Assign confidence tier A/B/C.
7. **Value scan.** Build `odds.json` (schema in odds-sourcing.md), then:
   ```
   python3 scripts/value.py --predict-json out.json --odds-json odds.json --budget 100
   ```
   The plan takes whatever has the highest EV — a correct score is a valid
   pick when the numbers say so. "NO VALUE — 观望" is a respectable output.
8. **Parlay (multi-match).** Run steps 1–7 per match (fan research out to
   sub-agents per match), collect one candidate leg per match into
   `legs.json`, then:
   ```
   python3 scripts/value.py --parlay legs.json --parlay-formats "3x1,4x11"
   ```
   Legs you're not sure about get dropped, not downweighted — the script
   enforces this (confidence C, prob < 0.55, or single-leg EV ≤ 0) and prints
   the exclusion reasons; put them in the report.
9. **Report** per `references/report-templates.md`: current date stamped at
   the top (data-as-of marker), verdict first, tables over prose, tight
   length, no emoji, sources with dates, bilingual disclaimer.

Consult `references/handicap-rules.md` whenever reading or writing any
handicap line, water level, or Chinese market terminology (平半/半一/受让…),
and for the supremacy↔line intuition tables.

## Guardrails

- **No personnel claims from memory.** Every injury, transfer, suspension, or
  lineup statement must come from a source found this session, with a date;
  stale (>14 days) personnel news must be re-verified. No source → no
  adjustment, and say so.
- **First-hand data only for parameters.** Official announcements, press
  conferences, lineups, stats databases (Tier 1/2). Other people's predictions
  are sentiment (Tier 3) — one line in Risks, zero weight in λ. Exception:
  style *descriptions* of a coach/team may support the style label.
- **All arithmetic goes through the scripts** — settlement, probabilities,
  EV, Kelly, parlays. If you catch yourself computing a quarter-ball payout
  or multiplying parlay odds in prose, stop and run the script.
- **Probabilities, never certainties.** Ranges plus a confidence tier. 必胜 /
  稳 / "lock" are banned. An honest "no value, don't bet" is a first-class
  answer.
- **Market scope is fixed**: 1X2, Asian handicap, CSL 让球胜平负, correct
  score. Do not analyze or price over/under totals, both-teams-to-score, or
  half-time/full-time markets, even when odds for them are visible.
- Reports: current date at the top, compact, no emoji, no AI-flavored filler
  (rules in report-templates.md), end with the 18+ responsible-gambling
  disclaimer in English and Chinese.
- Refuse match-fixing, insider-information, or "guaranteed win" requests.

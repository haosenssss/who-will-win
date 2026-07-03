# Quantification Recipe | 量化配方

How to turn research into two numbers — λ_home and λ_away (expected goals) —
reproducibly. Follow the eight steps in order. Every adjustment is bounded and
must cite a source found this session; if you cannot justify a step with
evidence, skip the adjustment rather than guess.

Why this exists: an LLM asked for "the probability Arsenal wins" freestyles a
number anchored to nothing. The same LLM asked to estimate attacking and
defensive rates against league baselines, with capped adjustments, produces
defensible λs — and `predict.py` turns λs into every market probability
deterministically.

## Step 1 — Collect rates

Preferred: xG per match and xGA per match, **home matches only for the home
team, away matches only for the away team**. Sources: FBref, Understat,
FotMob (see the search playbook).

Fallback when xG is unavailable (lower leagues): actual goals with shrinkage
toward the league mean, because small samples lie:

```
rate = (team_goals_total + 5 × league_avg_per_match) / (matches + 5)
```

## Step 2 — Blend recency

```
rate_used = 0.7 × season_rate + 0.3 × last6_rate
```

If fewer than 8 matches this season, blend 50/50 with last season (mind
promotion/relegation: shift one tier).

**Finishing regression check**: if actual goals exceed xG by >20% over the
season, the team is overshooting — use xG, not goals. Teams regress to their
xG; punters who chase hot finishing streaks pay for it.

## Step 3 — Multiplicative strength model

μ_home / μ_away = league average home / away goals per match. Verify current
season values by search when possible; fallback priors:

| League | μ_home | μ_away |
|---|---|---|
| Premier League | 1.65 | 1.35 |
| Bundesliga | 1.75 | 1.40 |
| La Liga | 1.50 | 1.15 |
| Serie A | 1.45 | 1.20 |
| Ligue 1 | 1.50 | 1.20 |
| 中超 CSL | 1.55 | 1.25 |
| J1 League | 1.40 | 1.15 |
| Cup/tournament knockout | 1.30 | 1.10 |
| Unknown league default | 1.50 | 1.20 |

```
Att_H = home_scoring_rate(H) / μ_home      Def_A = away_conceding_rate(A) / μ_home
Att_A = away_scoring_rate(A) / μ_away      Def_H = home_conceding_rate(H) / μ_away

λ_home_raw = μ_home × Att_H × Def_A
λ_away_raw = μ_away × Att_A × Def_H
```

For tournaments on neutral ground, use the knockout row and halve the home
advantage (set μ_home ≈ μ_away × 1.1 unless one side is effectively at home).

## Step 4 — Tier anchor cross-check

Classify both teams: **Elite** (title contenders, top ~15% by Elo/table),
**Strong** (European places), **Mid**, **Weak** (relegation zone). If computed
λ_home_raw deviates more than 0.3 from the band below, re-examine your inputs
before proceeding — a data error is far more likely than a genuine outlier.

λ_home_raw anchor bands (home tier × away tier):

| Home ↓ / Away → | Elite | Strong | Mid | Weak |
|---|---|---|---|---|
| Elite | 1.5–1.9 | 1.8–2.2 | 2.1–2.6 | 2.6–3.2 |
| Strong | 1.2–1.6 | 1.5–1.9 | 1.8–2.2 | 2.2–2.7 |
| Mid | 0.9–1.2 | 1.1–1.5 | 1.3–1.6 | 1.6–2.0 |
| Weak | 0.7–1.0 | 0.8–1.2 | 1.0–1.3 | 1.2–1.6 |

λ_away_raw: same table minus ≈ 0.25 (away sides score less at every tier).

## Step 5 — Apply match modifiers (bounded, sourced)

Each modifier is multiplicative and requires a Tier 1/2 source (see the
source-tier rules in `analysis-framework.md`). No source, no adjustment.

| Factor | Applies to | Bound | Rule |
|---|---|---|---|
| Star attacker out | own λ | ×0.85–0.95 | ×(1 − 0.5 × goal-involvement share), floor 0.85 |
| First-choice GK or 2+ starting defenders out | opponent λ | ×1.05–1.12 | scale with importance |
| Confirmed heavy rotation | own λ ×0.80–0.90, opp λ ×1.05 | | needs manager quote or trusted beat report |
| Rest differential ≥ 3 days | fresher side λ | ×1.03–1.06 | |
| Midweek continental away trip | own λ | ×0.95–0.98 | |
| Documented tactical edge | either λ | ±5–8% | must name the mechanism (e.g. high line vs pace) |
| Must-win with concrete evidence | own λ | ×1.00–1.05 | narrative alone is not evidence |
| Dead rubber | own λ | ×0.90–0.95 | |
| New-manager bounce (first 3 matches) | own λ | ×1.00–1.05 | |
| Extreme weather (confirmed forecast) | both λ | ×0.95 | |

**Hard cap: the cumulative product per team stays within [0.70, 1.30].**
Derbies and red-card-prone referees are variance flags for the report, never
multipliers — they widen uncertainty, they don't shift the mean.

## Step 6 — Estimate first, anchor second

Write the preliminary λs into your working notes **before** reading any
market odds. Then open the odds gathered earlier and compare (Layer 3 in
`analysis-framework.md`). This ordering is the discipline that stops you from
laundering the market's number through fake analysis — and from ignoring a
market that knows about a lineup leak you missed.

Reverse lookup for the comparison: the supremacy ↔ line table in
`handicap-rules.md`.

## Step 7 — Blend for value decisions

`value.py` prices every selection with:

```
p_blend = 0.65 × p_model + 0.35 × p_market_novig
```

The report shows pure model probabilities; recommendations run on the blend.
Rationale: LLM-derived probabilities are miscalibrated in predictable ways,
and the blend suppresses fake edges while keeping genuine, evidence-backed
divergences alive. Don't override `--blend` upward without a written reason.

## Step 8 — Scoreline style adjustment

λ sets how strong; style sets the shape of winning scorelines. From the
style profile built in `analysis-framework.md` (track-record deep-read),
pass a label to `predict.py`:

| Label | Meaning | Effect (1X2 invariant) |
|---|---|---|
| `controlled` 控场型 | shuts games down when ahead, manages margins | blowout (margin ≥3) mass shifts to 1–2 goal wins |
| `ruthless` 屠刀型 | keeps scoring, chases goal difference | narrow-win mass shifts to blowouts |
| `balanced` 均衡型 | default | no reshaping |

The label needs evidence: coach style search plus historical scoreline
distribution. When in doubt, `balanced`.

## Worked example (numbers verified through predict.py v1.0.0)

Arsenal (H) vs Liverpool, EPL. Current-season league averages found by
search: μ_home = 1.60, μ_away = 1.30.

Research yields: Arsenal home xG 2.0 / xGA 0.9 per match; Liverpool away
xG 1.7 / xGA 1.2 per match.

```
Att_H = 2.0/1.60 = 1.25     Def_A = 1.2/1.60 = 0.75
Att_A = 1.7/1.30 = 1.31     Def_H = 0.9/1.30 = 0.69

λ_home_raw = 1.60 × 1.25 × 0.75 = 1.50
λ_away_raw = 1.30 × 1.31 × 0.69 = 1.18
```

Anchor check: Elite vs Elite band 1.5–1.9 ✓ (home), away band ≈ 1.25–1.65
minus tier drift ✓.

Modifiers, each sourced:
- Liverpool's top scorer out (official club statement, 31% goal involvement):
  λ_away × max(0.85, 1 − 0.5×0.31) = ×0.85 → **1.00**
- Arsenal on 3 extra rest days (fixture lists): λ_home × 1.03 → **1.55**

```
python3 scripts/predict.py --home-lambda 1.55 --away-lambda 1.00
```

Output: 1X2 = **48.9% / 27.9% / 23.2%** (fair odds 2.05 / 3.58 / 4.31),
supremacy +0.55, top scorelines 1-1 (13.3%), 1-0 (10.9%), 2-0 (9.4%).
AH home −0.5 wins 48.9%; CSL 让一球 = 25.8% / 23.0% / 51.1%.

Market check: consensus line home −0.5 at even water implies supremacy
≈ +0.5 → divergence < 10pp on every outcome → passes calibration. Feed the
odds into `value.py` for the optimal-play scan.

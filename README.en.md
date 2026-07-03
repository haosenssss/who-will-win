# who-will-win

<p align="center">
  <img src="images/banner.png" alt="who-will-win" width="100%" />
</p>

**Football match prediction skill for Claude Code and compatible AI agents. One founding principle: it never makes things up.**

[中文说明](README.md) | **English**

Give it a fixture — it runs a large-scale research operation on both teams
(player-by-player availability sweep, tactical matchup, track-record
deep-read, coach style profiling), compresses the evidence into calibrated
expected goals, and prices every market with a closed-form Dixon-Coles
engine: win/draw/loss, double chance, Asian handicap (five-way quarter-ball
settlement), China Sports Lottery 让球胜平负, and exact scores. Give it an odds
screenshot and it picks the high-confidence, fairly-priced play — staying
inside the band where it can actually be right, then taking the better price
there. Give it several fixtures and it builds parlays — dropping any leg it
isn't sure about.

Across the whole pipeline the LLM does exactly one thing: estimate expected
goals within bounded, sourced rules. Every calculation that touches money —
the score matrix, quarter-ball settlement, vig removal, EV, Kelly, parlay
enumeration — runs in zero-dependency pure Python, without rolling a single
die.

## Prediction Pipeline

Four stages, from raw intelligence to high-confidence predictions and picks.
Every stage has a gate; every step leaves evidence.

---

### STAGE 01 — Large-Scale Intelligence Scouting

<p align="center">
  <img src="images/step1_scout.png" alt="Intelligence Scouting" width="80%" style="border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);" />
</p>

*Research depth is the product. Out of a sea of noise, only first-hand
evidence becomes a parameter. A single fixture routinely triggers dozens of
targeted searches, pushed forward by several parallel sub-agents at once.*

- **Team-level opening volley (Phase 1, 8–10 concurrent searches).** The
  instant a fixture arrives, the orchestrator fires 8–10 team-level searches
  in parallel: fixture lock (date / venue / first or second leg), league table
  and home-away splits, both squads' injury news, predicted lineups, tactical
  preview, market odds, and Chinese-source Asian-handicap injury intel. Get the
  fixture wrong and no downstream rigor can save it — so step one always nails
  the match itself down first.
- **Per-player sweep: one sub-agent per team (Phase 2).** This is the moat. For
  **every** projected starter and key substitute — 8–15 players per side — the
  dispatched sub-agent searches each name independently: still at the club, fit
  or carrying a knock, suspended, drained by international duty, recent ratings
  and goals. Each sub-agent collapses its findings into a structured
  availability table (player / role / available? / condition / source+date). A
  stale article's "full-strength squad" claim dies on a single player-level
  search.
- **Track-record deep-read + gap fill (Phase 3–4).** Read the last-5 match
  reports for each side one by one — not scoreline strings, but how the goals
  actually came and whether performance diverged from result (dominated but
  lost? smash-and-grab win?); read head-to-head for the style-clash pattern in
  the process, not the score; for knockouts, pull the team's and coach's record
  at the same stage; then a dedicated coach-style search. Finally fill the
  edges: xG, Elo, rest differential, weather, referee booking tendencies.
- **Three-tier source grading + anti-hallucination discipline.** Every source
  is graded: **Tier 1 fact** (official club/league announcements, press-
  conference quotes, published lineups, stats databases), **Tier 2 reporting**
  (beat reporters, training-ground observation, travel squads), **Tier 3
  sentiment** (prediction articles, expert picks, forum opinion). Only Tier 1/2
  first-hand sources may move a parameter; prediction pieces are demoted to
  sentiment with zero weight. No personnel claim from memory — every injury,
  transfer, or suspension must be found this session, with a date; anything
  older than 14 days is re-verified before use.

---

### STAGE 02 — Quantification & the Dixon-Coles Engine

<p align="center">
  <img src="images/step2_poisson.png" alt="Dixon-Coles Engine" width="80%" style="border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);" />
</p>

*Compress a thick evidence chain into two numbers: expected goals $\lambda_H$
and $\lambda_A$. Reproducible, auditable, testable.*

- **Eight-step bounded recipe → λ.** Split home/away xG and xGA → blend recency
  $0.7\times\text{season} + 0.3\times\text{last6}$ → multiplicative strength
  model with league priors
  $\lambda_H^{\text{raw}} = \mu_H \cdot Att_H \cdot Def_A$ → cross-check against
  a tiered anchor table → apply match modifiers (personnel, rotation, tactics,
  rest, motivation), **each modifier individually capped and the cumulative
  product hard-clamped to $[0.70, 1.30]$**. λ itself has a hard bound
  $(0.1, 6.0]$ and a warning band $[0.5, 3.5]$; step outside and it flags for
  re-derivation. Every step must cite evidence found this session — skip an
  adjustment rather than guess.
- **Estimate first, anchor second.** Iron rule: the preliminary λs are written
  down **before** any odds are read. That ordering is the discipline — it stops
  you laundering the market's number through fake analysis, and forces you to
  face a market that may know about a lineup leak you missed.
- **Closed-form Dixon-Coles analytic engine.** Pure Python, zero third-party
  dependencies. It runs **no Monte-Carlo simulation** — it solves the full
  score-probability matrix in closed form: the Dixon-Coles $\tau$ low-score
  correction with parameter $\rho$ (default $-0.10$) fixes standard Poisson's
  systematic underestimate of 0-0, 1-0 and other low scores; when truncated
  tail mass drops below $10^{-6}$ the matrix auto-expands and renormalizes, so
  lopsided blowouts never silently lose probability. Deterministic,
  reproducible, backed by 84 tests.
- **Style reweighting (1X2 strictly invariant).** A `controlled` coach (shuts
  games down when ahead) and a `ruthless` one (chases goal difference to the
  final whistle) reshape the scoreline **distribution** — moving mass between
  blowout and narrow wins *within the same team's win region* — while
  home/draw/away probabilities do not move a hair. That invariance is a test
  assertion, not folklore.
- **Full-market output in one pass.** 1X2 with fair odds, **double chance
  (1X/12/X2)**, the full Asian-handicap ladder (each quarter-ball line split
  into a five-way full-win / half-win / push / half-lose / full-lose settlement
  distribution, both sides independently), CSL 让球胜平负, and the complete
  exact-score matrix from 0-0 up plus the likeliest scorelines with their
  combined top-3 hit rate.

---

### STAGE 03 — De-Vig & the Confidence Gate

<p align="center">
  <img src="images/step3_filter.png" alt="De-Vig and Confidence Gate" width="80%" style="border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);" />
</p>

*The model gives true probabilities; the market gives odds with water in them.
This layer wrings the water out, then filters for picks that are both safe and
not underpriced — hit-rate first, not maximum expectation.*

- **Four-format odds recognition.** Auto-detects and converts European, Hong
  Kong, Malay, and Indonesian odds to a common decimal scale. Inputs that fall
  in the 1.0–1.25 decimal-vs-HK ambiguity zone raise a **hard error** demanding
  an explicit format — it never guesses, because one wrong guess silently
  corrupts every downstream number.
- **Dual de-vig: proportional + power.** Strips the bookmaker margin two ways;
  decisions use the **power method** — bisecting for the decay exponent
  $\gamma$ that solves $\sum_i(1/d_i)^\gamma = 1$ — which shrinks longshots more
  than favourites, correcting exactly the favourite-longshot bias the public's
  love of favourites creates, to recover fairer implied probabilities.
- **Confidence gate → best value in band.** Blend model and de-vigged market
  with $p_{\text{blend}} = 0.65\,p_{\text{model}} + 0.35\,p_{\text{market}}$,
  then two steps: (1) a **confidence gate** keeps only selections whose hit
  probability clears a floor (55% by default, tunable), shutting the door on
  low-probability longshots; (2) **best value in band** ranks the survivors so
  the better-priced safe pick surfaces first — not the trivial-payout 1.05
  favourite, not the 8.0 longshot. That sweet spot is the recommendation;
  scorelines are handled separately, the top 2-3 by probability with a combined
  hit rate.
- **Divergence discipline.** A model-vs-de-vigged-market gap above 10
  percentage points on any outcome forces a re-examination: missed team news?
  stale xG? a line moved by a lineup leak? A surviving divergence must carry a
  written "why the market is wrong" thesis in the report, or the estimate is
  pulled back to the market.
- **Hit-rate first, not max-EV.** EV, Kelly, and "no +EV, stand down" are still
  computed — but demoted to a secondary reference, no longer the headline. The
  goal is guessing right inside a controllable-risk band, not chasing a longshot
  for a positive-EV number. When nothing clears the floor, it says so plainly:
  "no high-confidence pick".

---

### STAGE 04 — Confidence-First Picks & Parlays

<p align="center">
  <img src="images/step4_portfolio.png" alt="Confidence-First Picks and Parlays" width="80%" style="border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);" />
</p>

*Choosing the safe pick is half the job; how to combine it, whether to bet, and
how much is the other half.*

- **Confidence-first picks.** The report leads not with the highest-EV longshot
  but with three things: the 2-3 most-likely scorelines (with combined hit
  rate), the safest 1X2 or double-chance cover, and the best-priced selection
  inside the confidence band. Be right first, worry about value second.
- **Fractional-Kelly sizing (secondary tool).** If you do stake, full-Kelly
  fraction from $f^* = \dfrac{bp - q}{b}$ scaled down by a conservative fraction
  (1/4 Kelly by default), each bet capped and combined exposure held to 6% of
  bankroll. This is a tool for those who choose to bet, not the point of the
  recommendation.
- **Five-state Kelly (quarter-ball).** A quarter-ball bet has no simple
  win/lose binary, so on the return distribution of its five settlement states
  (full-win / half-win / push / half-lose / full-lose) the script runs a
  **golden-section search** — 100 interval-shrinking iterations — for the
  fraction that maximizes log-growth $\mathbb{E}[\log(1+f\cdot r)]$ — not a
  two-state formula bent to fit.
- **Parlays: hit-rate first, unsure legs dropped.** Before combining, every leg
  clears three gates: confidence-C fixtures are dropped, blended probability
  below 0.55 is dropped, single-leg EV ≤ 0 is dropped — each exclusion listed
  with its reason. It enumerates every combination N-fold to N串M (a `4x11` is
  all eleven 2-to-4-leg subsets of four legs), recommends the higher-hit-rate
  smaller parlays first, and lists longer, lower-hit-rate combos separately as
  the high-odds options. Market scope is locked to 1X2, double chance, Asian
  handicap, CSL 让球, and correct score.

---

## What makes it different

- **Research depth is the product.** The skill orchestrates dozens of
  targeted web searches per match — including one search per expected starter
  on both squads, delegated to parallel sub-agents — and reads the last five
  match reports per team instead of trusting scoreline strings.
- **First-hand sources only.** Official announcements, press conferences,
  lineups, and stats databases drive the numbers. Other people's predictions
  are classified as sentiment (Tier 3) and never touch the parameters.
- **The LLM never does betting math.** It estimates expected goals from
  evidence, within bounded, documented adjustment rules. Bundled zero-
  dependency Python scripts handle everything numeric: the score matrix,
  five-way quarter-ball settlement, double chance, vig removal (power method),
  EV, fractional Kelly, and N串M parlay enumeration.
- **Style-aware scorelines.** Teams that shut games down at 2-0 and teams
  that chase goal difference get different scoreline distributions from the
  same win probability — profiled from coach history and press consensus, with
  win/draw/loss left unchanged.
- **Hit-rate first, honest fallback.** The goal is guessing right inside a
  controllable-risk band — clear a probability floor first, then take the
  better-priced pick among the safe ones, rather than chasing a longshot for a
  positive-EV number. Estimate-then-anchor discipline, mandatory re-examination
  on >10pp divergence, confidence tiers that gate recommendations; and when
  there is no high-confidence pick, it says so instead of forcing one.

## Install

### Claude Code

```bash
git clone https://github.com/haosenssss/who-will-win.git
cp -r who-will-win/skills/football-predictor ~/.claude/skills/
```

User-level goes in `~/.claude/skills/`; or per-project: copy into
`.claude/skills/` inside your repo.

### Codex / other agents

Any agent supporting the [Agent Skills](https://agentskills.io) format
(`SKILL.md` + `references/` + `scripts/`) can load
`skills/football-predictor/`. Codex CLI users can copy the folder into a
project and add a line to `AGENTS.md` pointing the agent at that directory's
`SKILL.md` for football predictions. Scripts need only the Python 3.8+ standard
library, no third-party dependencies.

### Let an AI install it (universal prompt)

Paste the block below to any AI coding agent (Claude Code, Codex, etc.) and it
will detect the environment, install the skill, and run a smoke test itself:

```text
Install the "who-will-win" football-prediction skill for me.

1. Clone https://github.com/haosenssss/who-will-win.git into a temp directory.
2. Detect the correct skills directory for THIS environment:
   - Claude Code: user-level ~/.claude/skills/  (or project-level .claude/skills/
     if I'm working inside a specific repo).
   - Any other agent that supports Agent Skills: use that agent's skills
     directory.
   - If no skills directory convention exists: copy into the current project and
     register it — add a line to AGENTS.md (or the equivalent config) telling the
     agent to read skills/football-predictor/SKILL.md when doing football
     predictions.
3. Copy the ENTIRE skills/football-predictor/ folder into that location,
   preserving its structure (SKILL.md + references/ + scripts/).
4. Verify Python: run `python3 --version` and confirm it is >= 3.8. Then run the
   smoke test:
   python3 <install-path>/skills/football-predictor/scripts/predict.py \
     --home-lambda 1.5 --away-lambda 1.1 --format markdown
   It must print a 1X2 probability table with no errors.
5. Report back the exact install location and tell me how to trigger the skill
   (e.g. ask "who wins Arsenal vs Liverpool this weekend?").
```

## Use

```
> Arsenal vs Liverpool this weekend — who wins?
> 帮我分析一下明晚国米对尤文，附截图是竞彩的让球赔率     [attach screenshot]
> I want a 3-fold accumulator from these matches: ..., ..., ...
```

The report is date-stamped at the top (data-as-of marker), leads with the
verdict, and shows the player-sweep table, model vs market comparison, top
scorelines, and — when odds are available — the high-confidence picks: the
likeliest scorelines, the safest 1X2 or double-chance cover, and the
best-priced selection inside the confidence band.

## Run the engine directly

```bash
# λ -> full-market probabilities and fair odds
python3 skills/football-predictor/scripts/predict.py \
  --home-lambda 1.55 --away-lambda 1.00 --home-name Arsenal --away-name Liverpool

# odds + model probabilities -> EV scan and fractional-Kelly stakes
python3 skills/football-predictor/scripts/value.py \
  --predict-json out.json --odds-json odds.json --budget 100

# multi-match parlay: drop ineligible legs and enumerate N串M packages
python3 skills/football-predictor/scripts/value.py \
  --parlay legs.json --parlay-formats "3x1,4x11"
```

## Repository layout

```text
skills/football-predictor/
├── SKILL.md                        skill entry point + guardrails (market scope, anti-hallucination)
├── references/
│   ├── analysis-framework.md       four-phase search playbook, three-layer funnel, source tiers
│   ├── quantification.md           eight-step bounded λ recipe, modifier caps, style reweighting
│   ├── handicap-rules.md           settlement rules per market, terminology, supremacy↔line tables
│   ├── odds-sourcing.md            screenshot transcription, odds-format recognition, odds.json schema
│   └── report-templates.md         report templates + anti-AI-flavor writing rules
└── scripts/
    ├── predict.py                  Dixon-Coles closed-form engine (λ → full-market probabilities)
    └── value.py                    de-vig / EV / fractional-Kelly / parlay engine
tests/     unit tests for predict and value
evals/     evaluation set for skill triggering and workflow
examples/  three worked examples: single match, screenshot odds, parlay
```

## Tests

```bash
python3 -m pytest tests/ -v
```

84 tests cover the Poisson/Dixon-Coles math, double-chance identities,
confidence-pick selection, an exhaustive quarter-ball settlement golden table,
odds-format conversions, vig removal (proportional and power), Kelly, and
parlay filtering.

## Disclaimer

18+. This project is for reference and entertainment only. Football is a
high-variance sport; no model guarantees profit. Never bet money you cannot
afford to lose. If gambling is a problem for you or someone near you, seek
help. Nothing here is financial advice.

## License

[MIT](LICENSE)

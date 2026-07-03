# Analysis Framework | 分析框架

The research methodology. It is a three-layer funnel, not a checklist:
**Layer 1 produces numbers, Layer 2 adjusts them within caps, Layer 3 checks
and never adjusts.** The depth of research is the product — the report is just
its compressed output.

Run the search playbook (§5) to gather evidence, classify every source by
tier (§6), then work the layers in order.

## 0. Fixture lock

Before anything else, confirm via search: exact fixture, competition, date
(check against today's date), kickoff time, venue, first or second leg,
aggregate score if a second leg. Cup and league meetings often fall in the
same week — if two plausible fixtures exist, ask the user which one. Echo the
locked fixture header before proceeding. Analyzing the wrong match is the one
error no downstream rigor can fix.

## 1. Layer 1 — Strength baseline

Produces raw λs via `quantification.md` steps 1–4. Gather:

- League table position, points per game, **home/away splits**
- Season xG/xGA per match (home-only for home team, away-only for away team
  when findable), plus last-6 trend
- Elo rating (ClubElo — fetchable, see §5)
- Finishing sustainability: goals vs xG gap → regression check

## 2. Layer 2 — Match modifiers

Six groups. Each adjustment is bounded per the table in `quantification.md`
step 5, and each requires a Tier 1/2 source found this session.

### 2.1 Personnel 人员

Injuries, suspensions, international-duty fatigue — weighted by the player's
goal-involvement share, not by name recognition. Distinguish confirmed
lineups (within ~60 min of kickoff) from predicted ones. This group is where
the per-player sweep (§5 Phase 2) pays off: a "fully fit squad" claim from a
stale article dies on one player-level search.

### 2.2 Rotation risk 轮换

Fixture congestion, a bigger match within 4 days, cup priorities. Requires a
manager quote or trusted beat report — never inferred purely from the
schedule.

### 2.3 Tactical matchup 战术匹配

Style pairing, not team quality: high press vs shaky build-up, low block vs
a side with no creativity between the lines, high defensive line vs pace in
behind, set-piece strength vs zonal weakness, manager head-to-head patterns.
Name the mechanism or make no adjustment.

### 2.4 Rest & travel 休息与旅途

Days since last match for each side; midweek continental away trips.
Mechanical and checkable — compute it from fixture lists, don't estimate it.

### 2.5 Motivation & context 动机

Stakes (title, relegation, European qualification, dead rubber), new-manager
bounce. "They really need this" is a narrative, not evidence — motivation
adjustments require something concrete: a mathematically dead rubber, an
announced rotation policy, a documented bonus structure. Derby intensity is a
**variance flag**, not a λ adjustment.

### 2.6 Track-record deep-read 往绩深读

The core differentiator. Numbers summarize outcomes; reading the matches
explains them. Four sub-modules:

**a. Recent-match review 近况复盘.** Read match reports for each side's last
3–5 games (not just scorelines): how the goals actually came, whether
performance diverged from result (dominated but lost? smash-and-grab win?),
in-game tactical shifts, momentum shape. A team on 4 points from 5 games
while out-xG-ing everyone is dangerous, not weak — this is where you catch
it before the market fully does.

**b. Head-to-head deep read 交锋史深读.** Process over results. Look for
style-clash patterns ("their high line got run in behind three straight
meetings"), whether a bogey-team effect has a tactical root or is noise.
Ignore H2H older than 3 years or under different managers. Weight cap ±5% —
H2H is tactical evidence, never an outcome predictor.

**c. Tournament pedigree 大赛往届战绩.** For cups and tournaments (World Cup,
Euros, Champions League knockouts): search the team's and the coach's record
at the same stage of the same competition — knockout scoreline distribution,
penalty-shootout history, comeback record, evidence for big-game or
big-game-bottler patterns. A side that has ground out four straight 1-0
knockout wins tells you how it plays these occasions.

**d. Team/coach style profile 风格画像.** Does this team keep pushing at 2-0
or shut the game down? Can it win big but chooses not to (squad preservation),
or does it chase goal difference to the final whistle? Two evidence tracks,
use both:
1. Historical scoreline distribution under this coach (blowout share of wins)
2. Dedicated style search (§5 Phase 3): press coverage, pundit and fan
   discussion of the coach's tendencies — coach styles are usually loudly
   documented; multi-source consensus is sufficient evidence

Output a label — `controlled` 控场型 / `ruthless` 屠刀型 / `balanced` 均衡型 —
and pass it to `predict.py` (quantification step 8). It reshapes scoreline
probabilities without touching win/draw/loss, which is exactly what this
phenomenon does in reality. Default `balanced` when evidence is thin.

## 3. Layer 3 — Calibration (checks only, no new adjustments)

1. **Estimate-then-anchor**: preliminary λs must be written down before
   reading market odds. Then compare model 1X2 vs the no-vig market.
2. **>10pp divergence on any outcome** triggers mandatory re-examination:
   Did you miss a team-news item? Is your xG stale? Is the line moved by a
   lineup leak? If the divergence survives re-examination, write an explicit
   "why the market is wrong" thesis into the report. No thesis, no edge —
   pull your estimate toward the market.
3. Sanity bands: draw probability 18–35% for normal matches; λ total 1.8–4.2;
   supremacy −1.5..+2.0. Outside a band → re-derive, don't rationalize.
4. Variance flags (derby, extreme weather, card-happy referee, two chaotic
   styles): widen stated ranges and note them in Risks — never shift the
   point estimate.
5. Assign a confidence tier, which gates betting recommendations downstream:

| Tier | Condition | Consequence |
|---|---|---|
| A | confirmed lineups published | full recommendations |
| B | >48h out, predicted lineups | normal; note what could change |
| C | data-poor league / missing key facts | no exact-score picks, Kelly fractions halved, leg excluded from parlays |

## 4. Multi-match / parlay workflow

Each match gets the full pipeline independently (fan the research out to
sub-agents per match when available). Per match, produce a candidate leg:
best selection, decimal odds, blended probability, confidence tier. Then
`value.py --parlay legs.json` filters and combines. The filter encodes the
house rule: **a leg you're not sure about doesn't get trimmed — it gets
dropped** (confidence C, blended prob < 0.55, or single-leg EV ≤ 0 → out,
with the reason printed).

## 5. Search playbook | 搜索手册

Research is the product — do not economize here. Batch searches in parallel
within each phase; use sub-agents where the harness supports them.

### Phase 1 — Team level (one parallel batch, 8–10 searches)

| # | Query template | Purpose |
|---|---|---|
| 1 | `{home} vs {away} {month year} kickoff venue` | fixture lock |
| 2 | `{league} table form {season}` | baseline |
| 3 | `{home} injury news team news {month year}` | personnel |
| 4 | `{away} injury news team news {month year}` | personnel |
| 5 | `{home} vs {away} predicted lineups` | XIs (near matchday) |
| 6 | `{home} vs {away} preview tactical analysis` | tactics; stats often aggregated |
| 7 | `{home} vs {away} odds` | market anchor — **fire now, read only after preliminary λ is written** |
| 8 | `{主队} vs {客队} 亚盘 伤停` | Chinese sources; strong for Asian markets |
| 9–10 | `{home} xG this season site:fbref.com` etc. | stats |

### Phase 2 — Per-player sweep (delegate to sub-agents)

For each expected starter and key substitute on **both** squads (8–15 players
per team): `{player} injury status form {month year}`. Verify: still at the
club, fit or carrying a knock, recent ratings/goals, international-duty
minutes. **Default orchestration: one sub-agent per team**, each running its
player searches in parallel and returning a structured availability table
(player / role / available? / condition / source+date). Without sub-agent
support, run the same queries in parallel batches from the main loop. This
phase is deliberately heavy — it is the moat.

### Phase 3 — Track record & style (can run as a third sub-agent)

- Match reports for each side's last 5 games, one search per match
- `{home} vs {away} head to head recent meetings`
- Tournament pedigree where applicable: `{team} {competition} knockout
  record`, `{coach} {competition} record`
- Coach style: `{coach} tactics style 风格 评价` — cross-verify the consensus
  against the historical scoreline distribution

### Phase 4 — Gap fill

xG lookups still missing, rest differential (`{team} last match date`),
weather at venue on matchday, referee appointment (big leagues, close to
kickoff only).

### Fetchable no-key sources (WebFetch)

| URL pattern | Gives |
|---|---|
| `https://api.clubelo.com/{TeamName}` | Elo history, plain CSV |
| `https://understat.com/team/{TeamName}/{year}` | xG, top-5 leagues + RFPL |
| `https://fbref.com/en/squads/...` | full stats (find URL via search first) |
| `https://www.football-data.co.uk/` | historical results CSVs |

### Findable vs wishful — do not chase ghosts

| Data | Realistically findable? |
|---|---|
| Table, form, results, H2H | Yes, reliably |
| Season xG/xGA (top leagues) | Yes |
| Injuries/suspensions | Yes — verify freshness, always |
| Predicted XIs | Within ~3 days of kickoff |
| Elo | Yes (CSV above) |
| Current consensus odds | Yes |
| Opening lines / line movement | **No** — except in user-provided comparison screenshots |
| PPDA, pressing metrics | Mostly no; optional, never required |
| Referee assignment | Big leagues, near matchday only |

## 6. Source tiers | 来源分级

First-hand data is the standard the user set. Every Layer 2 adjustment must
cite its tier; a Tier 3 citation in a parameter justification is a violation.

| Tier | What | Allowed use |
|---|---|---|
| **1 — Fact 事实级** | official club/league announcements, press-conference quotes, published lineups, stats databases (xG/Elo/results), match records | λ adjustments, all claims |
| **2 — Reporting 报道级** | beat reporters, training-ground observation, travel-squad lists | λ adjustments after date check |
| **3 — Sentiment 情绪级** | prediction articles, expert picks, tipster content, forum/贴吧 opinion | sentiment line in Risks only; zero weight in λ; contrarian context at most |

**Style-profile exception**: press/fan descriptions of a coach's or team's
*style* (not match predictions) are legitimate qualitative evidence for the
§2.6d style label when multiple sources agree. Any win/lose/score *prediction*
inside those same articles stays Tier 3.

Freshness rules: every cited source carries its date; embed the current month
and year in queries; anything older than 14 days on personnel must be
re-verified; before adjusting for any player, confirm the player is still at
the club this window.

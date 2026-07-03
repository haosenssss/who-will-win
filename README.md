# who-will-win

**Football match prediction skill for Claude Code and compatible AI agents.**

[中文文档](README.zh-CN.md)

Give it a fixture — it runs a large-scale research operation on both teams
(player-by-player availability sweep, tactical matchup, track-record
deep-read, coach style profiling), converts the evidence into calibrated
expected goals, and prices every market with a Dixon-Coles engine: win/draw/
loss, Asian handicap (quarter-ball settlement included), China Sports Lottery
让球胜平负, and exact scores. Give it an odds screenshot and it computes the
maximum-expected-value betting plan. Give it several fixtures and it builds
parlays — dropping any leg it isn't sure about.

## What makes it different

- **Research depth is the product.** The skill orchestrates dozens of
  targeted web searches per match — including one search per expected starter
  on both squads, delegated to parallel sub-agents — and reads the last five
  match reports per team instead of trusting scoreline strings.
- **First-hand sources only.** Official announcements, press conferences,
  lineups, and stats databases drive the numbers. Other people's predictions
  are classified as sentiment and never touch the parameters.
- **The LLM never does betting math.** It estimates expected goals from
  evidence, within bounded, documented adjustment rules. Bundled zero-
  dependency Python scripts handle everything numeric: the score matrix,
  quarter-ball settlement, vig removal (power method), EV, fractional Kelly,
  and N串M parlay enumeration.
- **Style-aware scorelines.** Teams that shut games down at 2-0 and teams
  that chase goal difference get different scoreline distributions from the
  same win probability — profiled from coach history and press consensus.
- **Honest by construction.** Estimate-then-anchor discipline against the
  market, mandatory re-examination on >10pp divergence, confidence tiers that
  gate recommendations, and "NO VALUE — don't bet" as a first-class result.

## Install

### Claude Code

```bash
git clone https://github.com/<you>/who-will-win.git
cp -r who-will-win/skills/football-predictor ~/.claude/skills/
```

Or per-project: copy into `.claude/skills/` inside your repo.

### Other agents

Any agent supporting the [Agent Skills](https://agentskills.io) format
(`SKILL.md` + `references/` + `scripts/`) can load
`skills/football-predictor/`. Scripts need only Python 3.8+ stdlib.

## Use

```
> Arsenal vs Liverpool this weekend — who wins?
> 帮我分析一下明晚国米对尤文，附截图是竞彩的让球赔率     [attach screenshot]
> I want a 3-fold accumulator from these matches: ..., ..., ...
```

The report leads with the verdict, shows the player-sweep table, model vs
market comparison, top scorelines, and — when odds are available — an
EV-ranked betting plan with fractional-Kelly stakes.

## Run the engine directly

```bash
python3 skills/football-predictor/scripts/predict.py \
  --home-lambda 1.55 --away-lambda 1.00 --home-name Arsenal --away-name Liverpool

python3 skills/football-predictor/scripts/value.py \
  --predict-json out.json --odds-json odds.json --budget 100
```

## Tests

```bash
python3 -m pytest tests/ -v
```

64 tests cover the Poisson/Dixon-Coles math, an exhaustive quarter-ball
settlement golden table, odds-format conversions, vig removal, Kelly, and
parlay filtering.

## Disclaimer

18+. This project is for reference and entertainment only. Football is a
high-variance sport; no model guarantees profit. Never bet money you cannot
afford to lose. If gambling is a problem for you or someone near you, seek
help. Nothing here is financial advice.

## License

[MIT](LICENSE)

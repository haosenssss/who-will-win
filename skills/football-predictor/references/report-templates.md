# Report Templates | 报告模板

The report is the compressed output of a large research operation. The
research can sprawl; the report cannot. Write in the language the user asked
in. **No emoji anywhere.** Visual devices allowed: markdown tables, Unicode
block bars (`████████░░ 52%`), horizontal rules.

## Length discipline

- Single-match report: lead with the verdict, keep the body tight — if a
  sentence doesn't change what the reader believes or does, delete it.
- Tables beat prose. Player sweep results go in a table, not paragraphs.
- Only list players/factors that carry weight. "Everyone else fit" is one
  line, not fifteen.

## Writing rules (anti-AI-flavor) | 反 AI 味写作规则

- No filler transitions: 值得注意的是 / 总体而言 / 综上所述 / 让我们拭目以待 /
  "It's worth noting" / "Overall" / "In conclusion" — banned.
- Replace empty adjectives with numbers: not 状态火热, but 近5场xG差+4.2仅拿4分.
- Open with the conclusion. Never recap at the end.
- No per-sentence hedging. Uncertainty lives in two places only: the
  confidence tier and the Risks section, stated concretely ("Salah's fitness
  decides ~6pp of home-win probability"), not as reflexive qualifiers.
- Opinions are welcome and must carry a probability. 必胜 / 稳单 / "lock" —
  banned.
- Cite as you claim: personnel facts carry source + date inline or in
  Sources.

## Single-match template

```markdown
# {Home} vs {Away} — {competition}, {date}

## 判决 | Verdict
{One sentence: the call.} 置信 {A/B/C}。
主胜 {p}% ████████░░ | 平 {p}% ███░░░░░░░ | 客胜 {p}% ██░░░░░░░░

## 关键情报 | Key Intel
| 球员 | 角色 | 状态 | 影响 | 来源 |
|---|---|---|---|---|
{only rows that matter}
{1-3 lines: rotation, rest differential, anything decisive — each with source+date}

## 往绩与风格 | Track Record & Style
- 近况：{substantive findings — performance vs results divergence, not W/L strings}
- 交锋：{style-clash pattern if one exists, else "无可用克制模式"}
- 大赛往届：{tournament pedigree, when applicable}
- 风格标签：{home: controlled/ruthless/balanced}、{away: …} — {one-line evidence each}

## 战术要点 | Tactical Keys
{1-2 deciding matchups, mechanism named}

## 概率与市场 | Model vs Market
λ: {home} {λh} / {away} {λa}（推导：{one line}）
| | 模型 | 市场(去水) | 差值 |
|---|---|---|---|
{home win / draw / away win rows}
{If any gap >10pp: the "why the market is wrong" thesis, or the walk-back}

## 比分 | Scorelines
{top 3-5 with probabilities; note style adjustment if applied}

## 收益最大化方案 | Optimal Play
{value.py plan table: pick / odds / EV / stake}
{or: "无正EV选项，观望。市场定价与模型一致。"}

## 风险 | Risks
- {variance flags, concretely}
- 舆情：{one line, Tier-3 aggregate, labeled as sentiment only}
- 最可能打脸的方式：{the specific failure scenario}

---
Sources: {source: date, …}
18+. For reference and entertainment only — no guarantee of profit. Bet only
what you can afford to lose. | 仅供参考娱乐，不构成投注建议。量力而行，理性投注。
```

## Multi-match / parlay addendum

After the per-match verdict blocks (each match gets a compressed version of
the single-match template — verdict, key intel, model vs market), add:

```markdown
## 串关方案 | Parlay Plan
入选腿：
| 场次 | 选项 | 赔率 | 概率 | 置信 |
|---|---|---|---|---|

剔除：
- {match}: {reason} — 拿不准的场次不进串

推荐组合：{legs} — 总赔率 {x}，命中 {p}%，EV {+x}%
{value.py parlay table for alternatives / N串M packages}
```

## Odds-only quick reply (user just pastes odds and asks 哪个划算)

Extraction table → echo-back if uncertain → vig per market → cross-market
consistency → honest statement: without match research, no-vig market
probabilities ARE the best estimate, so an odds-only read cannot find value —
offer the full pipeline. Keep it under ~15 lines.

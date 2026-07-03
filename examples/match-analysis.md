# Example — single match, no screenshot

> All data below is illustrative (fabricated fixture context, real engine
> numbers). It shows the workflow shape and the expected report format.

**User:** 这周末阿森纳主场对利物浦，帮我全面分析一下，谁会赢？

## What the agent did (condensed trace)

1. Fixture lock: EPL round 30, Saturday 17:30 local, Emirates. No cup clash.
2. Phase 1 batch: 9 parallel searches (injuries ×2, predicted XIs, tactical
   previews, table/form, odds — deferred reading, 中文亚盘伤停源).
3. Phase 2: two sub-agents, one per squad, 13 + 12 player-status searches →
   availability tables. Findings that mattered: Liverpool's top scorer
   (31% goal involvement) ruled out in Friday's official presser; Arsenal
   fully fit, 3 extra rest days.
4. Phase 3: last-5 match reports both sides; H2H process read; coach style
   searches → Arsenal `controlled` (12 league wins, only 2 by 3+ goals;
   consistent press descriptions of shutting games down), Liverpool
   `balanced`.
5. λ derivation (quantification.md): raw 1.50 / 1.18 from xG rates vs league
   baselines; modifiers: top scorer out ×0.85 (away), rest ×1.03 (home) →
   **λ 1.55 / 1.00**, written down before reading odds.
6. `predict.py --home-lambda 1.55 --away-lambda 1.00 --style-home controlled`
7. Market read: consensus 主让半球 high water ≈ supremacy +0.5. Model +0.55.
   No divergence > 10pp. Confidence B (lineups not yet official).
8. Odds auto-fetch found 1X2 at 2.30 / 3.50 / 3.20 → `value.py` scan.

## Final report

# Arsenal vs Liverpool — 英超第30轮，3月14日

## 判决
阿森纳小胜是最可能结局，萨拉赫缺阵让客队进攻降档。置信 B（首发未官宣）。
主胜 49% █████░░░░░ | 平 28% ███░░░░░░░ | 客胜 23% ██░░░░░░░░

## 关键情报
| 球员 | 角色 | 状态 | 影响 | 来源 |
|---|---|---|---|---|
| Salah | 利物浦头号得分手 | 缺阵（腿筋） | 客队31%进球参与，λ客 ×0.85 | 官方发布会 3/12 |
| Saliba | 阿森纳主力中卫 | 出战 | 无调整 | 跟队记者 3/12 |

阿森纳多休 3 天（上轮周二 vs 利物浦周五欧联客场），λ主 ×1.03。

## 往绩与风格
- 近况：利物浦近5场 xG 差 +3.1 但只拿 7 分，射术低于预期而非状态崩盘；阿森纳近5场零封3次。
- 交锋：近3次交锋利物浦高位线两次被身后球打穿，机制与本场阿森纳反击配置吻合。
- 风格标签：阿森纳 controlled（12胜中仅2场净胜3+，媒体一致描述领先后控场）；利物浦 balanced。

## 战术要点
利物浦失去萨拉赫后右路纵深威胁减半，阿森纳左后卫可以更高压上——这是本场最大的结构变化。

## 概率与市场
λ: Arsenal 1.55 / Liverpool 1.00（xG 基线 → 伤停与休息差修正，全部 Tier 1/2 来源）
| | 模型 | 市场(去水) | 差值 |
|---|---|---|---|
| 主胜 | 48.9% | 42.4% | +6.5pp |
| 平局 | 27.9% | 27.5% | +0.4pp |
| 客胜 | 23.2% | 30.1% | −6.9pp |

分歧 <10pp，但方向一致偏主队：市场可能尚未完全消化萨拉赫缺阵的定价（官宣仅12小时）。

## 比分
1-1 (13.3%)、1-0 (10.9%)、2-0 (9.4%)、2-1 (9.4%)。controlled 标签已将净胜3+比分质量转移至小胜。

## 收益最大化方案
| Pick | Odds | EV | Stake %bankroll |
|---|---|---|---|
| 1x2 主胜 | 2.30 | +6.1% | 1.2% |
| 亚盘 主 -0.25 | 1.98 | +5.1% | 1.7% |

同场选项相关，以主胜为主选。

## 风险
- 首发未官宣：若阿森纳中场轮换，主胜概率回落约4pp → 置信降C，建议观望。
- 舆情：主流预测文章一边倒看主队（仅情绪参考，未入参）。
- 最可能打脸的方式：利物浦低射术回归均值，客队效率反弹打出 0-1 偷袭。

---
Sources: 利物浦官方发布会 (3/12)、The Athletic 跟队 (3/12)、FBref xG (3/13)、ClubElo (3/13)
18+. For reference and entertainment only — no guarantee of profit. | 仅供参考娱乐，不构成投注建议。量力而行，理性投注。

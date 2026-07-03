# Example — odds screenshot as input

> Illustrative. Shows how a screenshot changes nothing about the pipeline —
> it is just the odds source, feeding the same research-backed analysis.

**User:** [screenshot of a betting page] 这场帮我看看哪个划算

## What the agent did (condensed trace)

1. **Transcribed the screenshot before any math:**

   | Market | Line | Prices |
   |---|---|---|
   | 欧赔 1X2 | — | 2.30 / 3.50 / 3.20 |
   | 亚盘 | 主让平半 (−0.25) | 0.98 / 0.90 (HK water) |
   | 比分 | 1-0 / 1-1 / 2-1 | 7.0 / 6.2 / 9.5 |

   All cells legible → no echo-back needed. Water levels identified by
   magnitude (0.90–0.98) and market type.
2. Cross-market consistency: 1X2 home 2.30 ≈ 43% implied ≈ supremacy +0.3;
   AH line 平半 (−0.25) agrees → extraction trusted.
3. Fixture identified from the screenshot header → full research pipeline ran
   exactly as in [match-analysis.md](match-analysis.md) → λ 1.55 / 1.00,
   confidence B.
4. Built `odds.json` from the transcription, ran `predict.py` + `value.py`.

## Final report (value section shown; analysis sections identical in form to the single-match example)

## 收益最大化方案

| Market | Selection | Odds | Model | Market | Blend | EV | Kelly |
|---|---|---|---|---|---|---|---|
| 1x2 | 主胜 | 2.30 | 48.9% | 42.4% | 46.1% | +6.1% | 0.047 |
| 亚盘 | 主 −0.25 | 1.98 | 48.9% | 48.9% | 46.0% | +5.1% | 0.067 |
| 1x2 | 平局 | 3.50 | 27.9% | 27.5% | 27.7% | −2.9% | — |
| 比分 | 2-1 | 9.50 | 9.4% | 10.5% | 9.8% | −7.1% | — |
| 比分 | 1-1 | 6.20 | 13.3% | 16.1% | 14.3% | −11.4% | — |

**方案（预算 100）**：主胜 1.2 单位 + 亚盘主平半 1.7 单位。两项同场相关，
以主胜为主选。比分玩法本场全部负 EV——截图里的比分赔率给得不高，不碰。

注：若模型与市场无显著分歧，正确输出是"无正EV选项，观望"。纯赔率、不做
调研的情况下，去水后的市场概率就是最优估计，找不出价值——需要完整分析
管线才有资格谈 EV。

18+. For reference and entertainment only — no guarantee of profit. | 仅供参考娱乐，不构成投注建议。量力而行，理性投注。

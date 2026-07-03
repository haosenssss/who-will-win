# Example — multi-match parlay 串关

> Illustrative. Four fixtures in, two legs survive the filter. The numbers
> below are real `value.py --parlay` output.

**User:** 这四场帮我串一个，能几串几就几串几：阿森纳vs利物浦、国米vs尤文、多特vs美因茨、里昂vs南特

## What the agent did (condensed trace)

1. Ran the full single-match pipeline on each fixture (research fanned out to
   sub-agents per match). Each match produced one candidate leg with blended
   probability and a confidence tier:

   | 场次 | 选项 | 赔率 | 概率 | 置信 |
   |---|---|---|---|---|
   | Arsenal vs Liverpool | 亚盘主 −0.25 | 1.98 | 0.575 | B |
   | Inter vs Juventus | 主胜 | 1.80 | 0.58 | A |
   | Dortmund vs Mainz | 竞彩让一球主胜 | 2.05 | 0.51 | B |
   | Lyon vs Nantes | 亚盘主 −0.5 | 1.87 | 0.56 | C |

2. `value.py --parlay legs.json --parlay-formats "3x1"`

## Final report (parlay section)

## 串关方案

剔除（拿不准的场次不进串）：
- Dortmund vs Mainz：让一球主胜概率 0.51 < 0.55 门槛——这场让一球太深，平盘才有把握
- Lyon vs Nantes：置信 C（法甲轮换信息缺失，首发无法核实）

推荐组合（2串1）：**阿森纳亚盘主平半 + 国米主胜**
总赔率 3.564，命中 33.4%，EV +18.9%，四分之一凯利注比 1.9%

3串1 无法成立：合格腿只有 2 条。宁可串小，不凑数——被剔除的两场单独观望。

跨场次按独立事件计算；串关方差随腿数陡增，命中率 33% 意味着三次里输两次
是正常波动，注比按此设定。

18+. For reference and entertainment only — no guarantee of profit. | 仅供参考娱乐，不构成投注建议。量力而行，理性投注。

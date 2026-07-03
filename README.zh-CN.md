# who-will-win 足球比赛预测

**给 Claude Code 及兼容 AI agent 使用的足球比赛预测 Skill。**

[English](README.md)

给它一场比赛——它会对两队发起一次大规模调研（逐球员可用性排查、战术对位、
往绩深读、教练风格画像），把证据压缩成校准过的预期进球数，再用 Dixon-Coles
引擎给出所有玩法的概率：胜平负、亚洲让球盘（含四分之一球结算）、中国竞彩
让球胜平负、以及具体比分。给它一张赔率截图，它会算出期望收益最大的下注方案。
给它多场比赛，它会构建串关——并且把拿不准的场次直接剔除。

## 差异化在哪

- **调研深度就是产品。** 每场比赛数十次定向搜索——包括对两队每一名预期首发
  逐人搜索状态（分派给并行子代理执行），并且逐场阅读两队近五场比赛报道，
  而不是只看比分串。
- **只认第一手数据。** 官方公告、发布会原话、首发名单、统计数据库驱动参数；
  别人的预测文章一律归为舆情信号，绝不进入计算。
- **LLM 从不做投注数学。** 它只负责在有界、有据的调整规则内估计预期进球；
  零依赖 Python 脚本处理所有数字：比分矩阵、四分之一球结算、去水（幂法）、
  期望值、分数凯利、N串M 串关枚举。
- **风格感知的比分预测。** 同样的胜率下，2-0 就收着踢的队和刷净胜球到最后
  一分钟的队，比分分布不一样——从教练历史和媒体共识中画像。
- **结构性诚实。** 先估后锚的纪律、与市场分歧超过 10 个百分点强制重审、
  置信分级控制推荐力度、"无价值——观望"是一等公民的结论。

## 安装

### Claude Code

```bash
git clone https://github.com/<you>/who-will-win.git
cp -r who-will-win/skills/football-predictor ~/.claude/skills/
```

也可以装到项目级：复制到仓库内的 `.claude/skills/`。

### 其他 agent

任何支持 Agent Skills 格式（`SKILL.md` + `references/` + `scripts/`）的
agent 都可以加载 `skills/football-predictor/`。脚本只需要 Python 3.8+
标准库。

## 使用

```
> 这周末阿森纳对利物浦，谁赢？
> 帮我分析一下明晚国米对尤文，附截图是竞彩的让球赔率     [附截图]
> 这三场帮我串一个三串一：……
```

报告以判决开头，包含逐球员排查表、模型与市场对比、最可能比分，以及（有赔率
时）按 EV 排序、带分数凯利注比的下注方案。

## 直接运行引擎

```bash
python3 skills/football-predictor/scripts/predict.py \
  --home-lambda 1.55 --away-lambda 1.00 --home-name Arsenal --away-name Liverpool

python3 skills/football-predictor/scripts/value.py \
  --predict-json out.json --odds-json odds.json --budget 100
```

## 测试

```bash
python3 -m pytest tests/ -v
```

64 个测试覆盖 Poisson/Dixon-Coles 数学、四分之一球结算黄金表穷举、赔率
四制式转换、去水、凯利公式与串关筛选。

## 免责声明

18+。本项目仅供参考与娱乐。足球是高方差运动，没有任何模型能保证盈利。
永远不要投入你输不起的钱。如果博彩已经对你或你身边的人造成困扰，请寻求
帮助。本项目不构成任何投注或财务建议。

## 许可证

[MIT](LICENSE)

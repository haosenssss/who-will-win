# who-will-win 足球比赛预测

<p align="center">
  <img src="images/banner.png" alt="who-will-win" width="100%" />
</p>

**给 Claude Code 及兼容 AI agent 使用的足球比赛预测 Skill。立身之本只有一条：绝不瞎说。**

**中文说明** | [English](README.en.md)

给它一场比赛——它会对两队发起一次大规模调研（逐球员可用性排查、战术对位、
往绩深读、教练风格画像），把证据压缩成校准过的预期进球数，再用闭式
Dixon-Coles 引擎给出所有玩法的概率：胜平负、双重机会、亚洲让球盘（含四分之
一球五态结算）、中国竞彩让球胜平负、以及具体比分。给它一张赔率截图，它会挑
出高把握、赔率又相对划算的选择——先卡在能猜对的概率区间里，再在里面选价更
好的。给它多场比赛，它会构建串关——并且把拿不准的场次直接剔除。

整条管线里，LLM 只做一件事：在有界、有据的规则内估计预期进球。所有涉及钱
的数学——比分矩阵、四分之一球结算、去水、期望值、凯利、串关枚举——全部交给
零依赖的纯 Python 脚本，一个随机数都不掷。

## 预测管线 (Prediction Pipeline)

四个阶段，从原始情报到高把握的预测与选择，环环有闸门、步步留证据。

---

### STAGE 01 — 大规模情报侦察 (Large-Scale Intelligence Scouting)

<p align="center">
  <img src="images/step1_scout.png" alt="Intelligence Scouting" width="80%" style="border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);" />
</p>

*调研深度就是产品。海量噪音里，只有第一手证据能变成数理参数。一场比赛动辄
数十次定向搜索，由多路并行子代理同时推进。*

- **球队级并行开火 (Phase 1，8–10 路并发)。** 收到比赛的一瞬间，Orchestrator
  一次性并行射出 8–10 条队级搜索：赛事锁定（日期/场地/首回合还是次回合）、
  联赛榜单与主客场分项、双方伤停、预测首发、战术前瞻、市场赔率、以及中文源
  的亚盘伤停情报。赛事一旦搞错，后面再精密也救不回来——所以第一步永远是把
  比赛本身钉死。
- **逐球员横扫：每队一个子代理 (Phase 2)。** 这是护城河。对**每一名**预期首发
  和关键替补——每队 8–15 人——派出的子代理逐人独立搜索：是否仍在队、有无伤
  病或带伤、停赛、国家队征调的体能消耗、近期评分与进球。每个子代理把结果收敛
  成一张结构化可用性表（球员 / 角色 / 是否可用 / 状态 / 来源+日期）。一篇旧稿
  一句"全主力"，会在一次球员级搜索面前当场破功。
- **往绩深读 + 补漏 (Phase 3–4)。** 逐场精读双方近 5 场比赛报道——不是看比分
  串，而是看进球怎么来的、表现与结果是否背离（碾压却输球？偷袭得手？）；交锋
  史只看过程里的克制模式，不看比分本身；杯赛淘汰赛还要查球队与教练在同一阶段
  的历史战绩模式；再对教练做风格专项检索。最后补齐 xG、Elo、休息天数差、天气、
  裁判牌风等边缘扰动项。
- **三级来源分级 + 反幻觉纪律。** 每条来源强制分级：**Tier 1 事实级**（官方
  公告、发布会原话、首发名单、统计数据库）、**Tier 2 报道级**（跟队记者、训练
  场观察、随队名单）、**Tier 3 情绪级**（预测文章、专家推介、论坛贴吧）。只有
  Tier 1/2 第一手来源才能进参数；预测文章一律降级为舆情信号，零权重。人员信息
  禁止凭记忆——每一条伤停/转会/停赛都必须是本会话搜到、且带日期；超过 14 天的
  旧闻强制重新核验。

---

### STAGE 02 — 证据量化与 Dixon-Coles 引擎 (Quantification & Dixon-Coles Engine)

<p align="center">
  <img src="images/step2_poisson.png" alt="Dixon-Coles Engine" width="80%" style="border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);" />
</p>

*把厚厚的证据链压缩成两个数：主客队的预期进球 $\lambda_H$、$\lambda_A$。可复现、
可审计、可测试。*

- **八步有界配方 → λ。** 拆分主客场 xG/xGA → 近因混合
  $0.7\times\text{赛季} + 0.3\times\text{近6场}$ → 带联赛先验的乘法强度模型
  $\lambda_H^{\text{raw}} = \mu_H \cdot Att_H \cdot Def_A$ → 分档锚定表交叉检验
  → 逐项修正（人员、轮换、战术、休息、动机），**每项修正有独立上限，累计乘积
  硬夹在 $[0.70, 1.30]$**。λ 本身还有硬边界 $(0.1, 6.0]$ 与警告区 $[0.5, 3.5]$，
  越界即报警重推。每一步都必须能引用当次会话找到的证据，宁可跳过也不瞎编。
- **先估后锚。** 铁律：预备 λ 必须在**看任何赔率之前**写下来。这一步顺序是纪律
  的核心——它既防止把市场的数字洗一遍冒充成自己的分析，也逼你正视一个可能比你
  更早知道首发泄露的市场。
- **闭式 Dixon-Coles 解析引擎。** 纯 Python、零第三方依赖。它不做任何蒙特卡洛
  模拟——而是**闭式解析**地算出整张比分概率矩阵：Dixon-Coles 的 $\tau$ 低比分
  修正项配合 $\rho$ 参数（默认 $-0.10$）纠正标准泊松对 0-0、1-0 这类小比分的
  系统性低估；矩阵尾部质量低于 $10^{-6}$ 时自动扩栏并重新归一化，冷门大比分也
  不会悄悄丢概率。确定性、可复现、由 84 个测试背书。
- **风格重加权（1X2 严格不变）。** 控场型（领先就收）与屠刀型（刷净胜球到最后
  一分钟）的教练画像会改变比分**分布形状**——在同一支球队的获胜区内，把大胜
  质量与小胜质量互相搬移——但胜/平/负三向概率分毫不动。这是测试断言的不变量，
  不是玄学。
- **一次输出全盘口。** 胜平负及公平赔率、**双重机会（1X/12/X2）**、亚盘全线
  阶梯（每条四分之一球线拆成全赢/半赢/走盘/半输/全输五态结算分布，主客两侧
  独立）、竞彩让球胜平负、以及 0-0 起的完整精确比分矩阵与最可能比分（含 top-3
  合计命中率）。

---

### STAGE 03 — 去水与置信筛选 (De-Vig & Confidence Gate)

<p align="center">
  <img src="images/step3_filter.png" alt="De-Vig and Confidence Gate" width="80%" style="border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);" />
</p>

*模型给出真实概率，市场给出含水赔率。这一层先把水挤干，再筛出"够稳、又不亏"
的选择——命中优先，不是追高期望。*

- **四制式赔率识别换算。** 自动识别欧洲盘、香港盘、马来盘、印尼盘并统一换算为
  十进制赔率。落在 1.0–1.25 这种十进制与港盘水位歧义区间的输入，脚本**硬报错**
  要求显式指定格式，绝不猜——猜错一次，下游每个数字都被悄悄污染。
- **双法去水：比例法 + 幂法。** 同时用比例法和幂法两种口径剥离庄家抽水；决策
  一律采用**幂法**——它二分逼近求解衰减指数 $\gamma$（解 $\sum_i(1/d_i)^\gamma=1$），
  对冷门的压缩强于对热门，正好修正大众追捧热门造成的"热门-冷门偏差"，还原出
  更公允的市场隐含概率。
- **置信闸门 → 区间内择优。** 先把模型概率与去水市场概率按
  $p_{\text{blend}} = 0.65\,p_{\text{model}} + 0.35\,p_{\text{market}}$ 融合，
  再走两步：① **置信闸门**——只保留命中概率高于下限（默认 55%，可调）的选项，
  把冷门长赔挡在门外；② **区间内择优**——在够稳的选项里优先选赔率更好的，既不
  推 1.05 那种没意思的大热门，也不追 8.0 的长赔。这个"甜点区"就是最终推荐；
  比分则单独按概率取前 2–3 个，给合计命中率。
- **分歧纪律。** 模型与去水市场在任一结果上偏离超过 10 个百分点，强制重审：是
  漏了球队新闻，还是 xG 过时，还是盘口被首发泄露带动了？幸存下来的分歧，必须在
  报告里写清"市场为什么错"的论点，否则把估计拉回市场。
- **命中优先，不是 EV 最大化。** 期望值、凯利、"无正 EV 就观望"仍然会算——但
  降级为次要参考，不再是头号结论。目标是在可控风险区间内尽量猜对，而不是为了
  一个正 EV 数字去押冷门。真找不到够稳的选择，就照实说"没有高把握选项"。

---

### STAGE 04 — 高把握优选与串关 (Confidence-First Picks & Parlays)

<p align="center">
  <img src="images/step4_portfolio.png" alt="Confidence-First Picks and Parlays" width="80%" style="border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.4);" />
</p>

*选出够稳的选择只是一半，另一半是怎么组合、要不要下、下多少。*

- **命中优先优选。** 报告的头牌不是某个 EV 最高的冷门，而是三样东西：最可能的
  2–3 个比分（附合计命中率）、最稳的胜平负或双重机会兜底选择、以及置信区间内
  价格最好的那个。先能猜对，再谈划算。
- **分数凯利仓位（次要工具）。** 如果要落到注比，用凯利公式
  $f^* = \dfrac{bp - q}{b}$ 算全额注比，再乘保守的分数系数（默认 1/4 凯利），
  单注设上限、组合总仓位封顶本金 6%。这是给愿意下注的人的工具，不是推荐重点。
- **五态凯利（四分之一球）。** 亚盘四分之一球注单没有简单的输赢二态，脚本在
  全赢/半赢/走盘/半输/全输五种结算状态构成的收益分布上，用**黄金分割法
  （Golden-Section Search）一维搜索**——100 次区间收缩迭代——求解使对数增长
  $\mathbb{E}[\log(1+f\cdot r)]$ 最大的注比，不是套用二态公式糊弄。
- **串关：命中优先，拿不准就剔除。** 组串前每条腿过三道闸：置信 C 的场次剔除、
  混合概率低于 0.55 剔除、单腿 EV ≤ 0 剔除，每条剔除都列明理由。N串1 到 N串M
  全枚举（如 4串11 即 4 条腿里所有 2–4 串的 11 个组合），优先推荐命中率高的小串，
  腿数越多命中率越低、只作为高赔选项另列。玩法范围锁死在胜平负、双重机会、亚盘、
  竞彩让球、精确比分。

---

## 差异化在哪

- **调研深度就是产品。** 每场比赛数十次定向搜索——包括对两队每一名预期首发
  逐人搜索状态（分派给并行子代理执行），并且逐场阅读两队近五场比赛报道，
  而不是只看比分串。
- **只认第一手数据。** 官方公告、发布会原话、首发名单、统计数据库驱动参数；
  别人的预测文章一律归为舆情信号（Tier 3），绝不进入计算。
- **LLM 从不做投注数学。** 它只负责在有界、有据的调整规则内估计预期进球；
  零依赖 Python 脚本处理所有数字：比分矩阵、四分之一球五态结算、双重机会、
  去水（幂法）、期望值、分数凯利、N串M 串关枚举。
- **风格感知的比分预测。** 同样的胜率下，2-0 就收着踢的队和刷净胜球到最后
  一分钟的队，比分分布不一样——从教练历史和媒体共识中画像，且胜平负概率不变。
- **命中优先，诚实兜底。** 目标是在可控风险区间内尽量猜对——先卡命中概率下限，
  再在够稳的选项里挑赔率更好的，而不是为一个正 EV 数字去押冷门。先估后锚、
  与市场分歧超 10 个百分点强制重审、置信分级控制推荐力度；真没有高把握选择，
  就照实说，绝不硬凑。

## 安装

### Claude Code

```bash
git clone https://github.com/haosenssss/who-will-win.git
cp -r who-will-win/skills/football-predictor ~/.claude/skills/
```

用户级装到 `~/.claude/skills/`；也可以装到项目级：复制到仓库内的
`.claude/skills/`。

### Codex / 其他 agent

任何支持 Agent Skills 格式（`SKILL.md` + `references/` + `scripts/`）的 agent
都能加载 `skills/football-predictor/`。Codex CLI 用户可把该目录拷进项目，并在
`AGENTS.md` 里加一行，指引 agent 在做足球预测时先读该目录的 `SKILL.md`。脚本
只需要 Python 3.8+ 标准库，无任何第三方依赖。

### 让 AI 自己装（万能安装 prompt）

把下面这段直接复制粘贴给任何 AI 编码 agent（Claude Code、Codex 等），它会自己
识别环境、装好并跑冒烟测试：

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

## 使用

```
> 这周末阿森纳对利物浦，谁赢？
> 帮我分析一下明晚国米对尤文，附截图是竞彩的让球赔率     [附截图]
> 这三场帮我看看怎么串一下：……
```

报告顶部标注分析日期（数据截至标记），以判决开头，包含逐球员排查表、模型与
市场对比、最可能比分，以及（有赔率时）高把握优选：最可能的几个比分、最稳的
胜平负或双重机会兜底、以及置信区间内价格最好的选择。

## 直接运行引擎

```bash
# 由 λ 生成全盘口概率与公平赔率
python3 skills/football-predictor/scripts/predict.py \
  --home-lambda 1.55 --away-lambda 1.00 --home-name Arsenal --away-name Liverpool

# 赔率 + 模型概率 → EV 扫描与分数凯利注单
python3 skills/football-predictor/scripts/value.py \
  --predict-json out.json --odds-json odds.json --budget 100

# 多场串关：剔除不合格腿并枚举 N串M 组合
python3 skills/football-predictor/scripts/value.py \
  --parlay legs.json --parlay-formats "3x1,4x11"
```

## 仓库结构

```text
skills/football-predictor/
├── SKILL.md                        技能入口与护栏（市场范围、反幻觉纪律）
├── references/
│   ├── analysis-framework.md       四阶段搜索手册、三层漏斗、来源三级分级
│   ├── quantification.md           八步有界 λ 配方、修正上限、风格重加权
│   ├── handicap-rules.md           各盘口结算规则、盘口术语、supremacy↔盘口
│   ├── odds-sourcing.md            截图转录、赔率格式识别、odds.json 结构
│   └── report-templates.md         报告模板与反 AI 味写作规则
└── scripts/
    ├── predict.py                  Dixon-Coles 闭式引擎（λ → 全盘口概率）
    └── value.py                    去水 / EV / 分数凯利 / 串关引擎
tests/     predict 与 value 的单元测试
evals/     技能触发与流程的评测集
examples/  单场分析、截图赔率、串关三个范例
```

## 测试

```bash
python3 -m pytest tests/ -v
```

84 个测试覆盖 Poisson/Dixon-Coles 数学、双重机会恒等式、置信优选筛选、
四分之一球结算黄金表穷举、赔率四制式转换、去水（比例法与幂法）、凯利公式与
串关筛选。

## 免责声明

18+。本项目仅供参考与娱乐。足球是高方差运动，没有任何模型能保证盈利。
永远不要投入你输不起的钱。如果博彩已经对你或你身边的人造成困扰，请寻求
帮助。本项目不构成任何投注或财务建议。

## 许可证

[MIT](LICENSE)

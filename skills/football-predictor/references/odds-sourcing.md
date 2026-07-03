# Odds Sourcing | 赔率获取

Odds feed the optimal-play section of every report. They come from one of
three routes, in order of preference. Whatever the route, the end product is
the same: an `odds.json` file passed to `value.py`.

## Route 1 — User screenshot 截图

The screenshot is a data source, not a separate workflow — extract the odds,
then run the normal pipeline.

### Extraction protocol (in this order)

1. **Transcribe everything before computing anything.** Convert the entire
   screenshot into a structured table: bookmaker / market type / line /
   prices / any 初盘 vs 即盘 (opening vs current) columns. No mental math
   during transcription.
2. **Echo-back gate.** If any cell is uncertain — blur, crop, ambiguous
   column headers — show the user the extracted table and ask them to confirm
   before proceeding. Odds misreads are the single most common failure mode
   of this workflow, and a wrong water level poisons every number downstream.
3. **Identify the handicap side by team name, never by row position.**
   受让 prefix = receiving = positive line. If the screenshot shows 主让半球,
   the home line is −0.5 regardless of layout.
4. **Distinguish water levels from decimal odds** by magnitude and market:
   HK water clusters in 0.75–1.15 on two-way markets; 3-way decimal prices
   run ~1.2–15. Values in 1.0–1.25 are ambiguous — ask, or pass
   `--odds-format` explicitly. `value.py` refuses to guess.

### Market auto-detection

| Signal in the image | Market |
|---|---|
| 3 prices, labels 胜/平/负 or 1/X/2 or H/D/A, no line | European 1X2 |
| 2–3 prices labelled 1X/12/X2 or 双重机会/双胜, all ~1.05–1.5 | Double chance |
| 让球 ±N + 3 prices, decimal ~1.5–5 | CSL 让球胜平负 |
| 2 prices in 0.75–1.15 + line words 平手/平半/半球/半一/一球… | Asian handicap, HK water |
| Grid of scorelines with prices | Correct score 比分 |
| Bookmaker rows (澳门/皇冠/bet365/立博…) with 初盘/即盘 columns | Odds-comparison page — extract opening AND current; this unlocks line-movement reading, otherwise unavailable |

### Cross-market consistency check (built-in misread detector)

Before trusting the extraction, check that the 1X2 prices and the AH line
imply roughly the same supremacy (use the intuition table in
`handicap-rules.md`). Example: 1X2 home 1.65 implies ~57% ≈ supremacy +0.75,
so the AH line should sit near 半一 (−0.75). If the extracted AH says −0.25,
the most likely explanation is a transcription error, not a market
inefficiency — re-read the image before concluding anything about value.

## Route 2 — Web auto-fetch (no screenshot)

Best-effort. Search `{home} vs {away} odds` and `{比赛} 亚盘 赔率`, extract
current mainstream prices from reachable pages. Rules:

- Record the source and a timestamp for every extracted price; both appear
  in the report ("odds as of …, via …").
- Consensus over outliers: if several books are visible, take a
  representative mid price, not the friendliest one.
- Opening lines and historical movement are **not** reliably fetchable — do
  not burn searches chasing them (they only arrive via Route 1 comparison
  screenshots).

## Route 3 — No odds available

State plainly in the report: "no market odds available — model fair odds
only", print `predict.py` fair odds, and **skip the optimal-play section**.
Never fabricate representative odds.

## Building `odds.json`

```json
{
  "format": "decimal",
  "one_x_two": [2.05, 3.60, 3.80],
  "double_chance": {"1X": 1.28, "12": 1.30, "X2": 1.55},
  "asian_handicap": [
    {"line": -0.5, "home": 0.95, "away": 0.93, "format": "hk"}
  ],
  "csl": [
    {"handicap": -1, "odds": [3.10, 3.55, 2.05]}
  ],
  "correct_score": {"1-0": 7.5, "2-1": 9.0, "1-1": 6.5}
}
```

- Order is always home/draw/away for 3-way markets.
- `double_chance` is an object keyed by cover (`1X`/`12`/`X2`); include only
  the covers you have. Its covers overlap, so `value.py` compares each against
  its raw implied rather than de-vigging them as a set.
- Any market may be omitted; `value.py` scans whatever is present.
- Per-entry `format` overrides the file default (common: decimal 1X2 next to
  HK-water handicaps on the same screenshot).
- Correct-score sets from screenshots are usually incomplete (no "other"
  bucket) — `value.py` detects booksum < 1 and falls back to raw implied
  probabilities for those rows, tagging them accordingly.

Then:

```
python3 scripts/value.py --predict-json out.json --odds-json odds.json [--budget 100]
```

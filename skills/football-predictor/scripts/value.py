#!/usr/bin/env python3
"""Value engine: odds + model probabilities -> EV scan, stakes, parlays.

Three modes:
  portfolio  --predict-json out.json --odds-json odds.json
             Scan every priced selection, find +EV plays, build the
             max-expected-return plan with fractional-Kelly stakes.
  single     --market 1x2|ah|csl|score --odds "..." (+ --predict-json)
  parlay     --parlay legs.json
             Filter legs (low-confidence legs are dropped, with reasons),
             enumerate N-fold combos and N串M packages.

Stdlib only. All betting arithmetic lives in scripts, never in LLM prose.
"""

import argparse
import itertools
import json
import math
import sys

VALUE_VERSION = "1.0.0"

LONGSHOT_ODDS = 4.0          # above this, EV threshold doubles
DEFAULT_MIN_LEG_PROB = 0.55  # parlay legs below this are dropped
DEFAULT_MIN_CONFIDENCE = 0.55  # confidence-mode floor: keep picks above this
PORTFOLIO_TOTAL_CAP = 0.06   # combined stakes never exceed 6% of bankroll
DISCLAIMER = ("18+. For reference and entertainment only — no guarantee of "
              "profit. Bet only what you can afford to lose. | "
              "仅供参考娱乐，不构成投注建议。量力而行，理性投注。")


# ---------- odds conversion ----------

def to_decimal(value, fmt):
    if fmt == "decimal":
        d = value
    elif fmt == "hk":
        d = value + 1.0
    elif fmt == "malay":
        d = 1.0 + value if value > 0 else 1.0 + 1.0 / abs(value)
    elif fmt == "indo":
        d = 1.0 + value if value >= 1.0 else 1.0 + 1.0 / abs(value)
    else:
        raise SystemExit(f"error: unknown odds format {fmt!r}")
    if d <= 1.0:
        raise SystemExit(f"error: odds {value} ({fmt}) convert to decimal "
                         f"{d:.3f} <= 1.0 — check format")
    return d


def detect_format(values):
    """Best-effort format hint. Ambiguous inputs must error, never guess."""
    if any(v < 0 for v in values):
        return "malay" if all(abs(v) <= 1.0 for v in values if v < 0) else "indo"
    if all(v >= 1.25 for v in values):
        return "decimal"
    if all(0 < v < 1.0 for v in values):
        return "hk"
    raise SystemExit(
        "error: odds values are ambiguous between decimal and HK "
        f"({values}) — pass --odds-format explicitly")


def convert_all(values, fmt=None):
    fmt = fmt or detect_format(values)
    return [to_decimal(v, fmt) for v in values], fmt


# ---------- vig removal ----------

def novig_proportional(decimals):
    inv = [1.0 / d for d in decimals]
    s = sum(inv)
    return [p / s for p in inv]


def novig_power(decimals, tol=1e-10):
    """Solve sum((1/d_i)^gamma) = 1 by bisection.

    The power method shrinks longshots more than favourites, correcting
    the favourite-longshot bias that proportional normalization ignores.
    """
    inv = [1.0 / d for d in decimals]
    lo, hi = 0.5, 8.0
    for _ in range(200):
        mid = (lo + hi) / 2
        s = sum(p ** mid for p in inv)
        if abs(s - 1.0) < tol:
            break
        if s > 1.0:
            lo = mid
        else:
            hi = mid
    return [p ** mid for p in inv]


def overround(decimals):
    return sum(1.0 / d for d in decimals) - 1.0


# ---------- EV & Kelly ----------

def ev_binary(p, d):
    """EV per unit stake for a simple win/lose selection."""
    return p * (d - 1.0) - (1.0 - p)


def ev_ah(dist, d):
    """EV per unit stake from a five-way AH settlement distribution."""
    return (dist["full_win"] * (d - 1.0)
            + dist["half_win"] * (d - 1.0) / 2.0
            - dist["half_lose"] * 0.5
            - dist["full_lose"])


def kelly_binary(p, d):
    f = (p * d - 1.0) / (d - 1.0)
    return max(0.0, f)


def kelly_ah(dist, d):
    """Maximize E[log(1 + f*r)] over the 5-outcome return distribution."""
    outcomes = [(dist["full_win"], d - 1.0),
                (dist["half_win"], (d - 1.0) / 2.0),
                (dist["push"], 0.0),
                (dist["half_lose"], -0.5),
                (dist["full_lose"], -1.0)]

    def growth(f):
        total = 0.0
        for p, r in outcomes:
            if p <= 0:
                continue
            v = 1.0 + f * r
            if v <= 0:
                return -math.inf
            total += p * math.log(v)
        return total

    lo, hi = 0.0, 0.99
    phi = (math.sqrt(5) - 1) / 2
    a, b = hi - phi * (hi - lo), lo + phi * (hi - lo)
    for _ in range(100):
        if growth(a) < growth(b):
            lo = a
        else:
            hi = b
        a, b = hi - phi * (hi - lo), lo + phi * (hi - lo)
    f = (lo + hi) / 2
    return f if growth(f) > growth(0.0) else 0.0


def blend_probs(model, market, blend):
    """Blend two probability vectors of equal length (both sum to 1)."""
    return [blend * m + (1.0 - blend) * q for m, q in zip(model, market)]


def blend_ah_dist(dist, q_market, blend):
    """Blend an AH 5-way distribution toward the market on the
    conditional win-given-decided scale, keeping neutral mass fixed."""
    w = dist["full_win"] + 0.5 * dist["half_win"]
    l = dist["full_lose"] + 0.5 * dist["half_lose"]
    if w + l <= 0:
        return dist
    c_model = w / (w + l)
    c = blend * c_model + (1.0 - blend) * q_market
    scale_w = (c * (w + l)) / w if w > 0 else 0.0
    scale_l = ((1.0 - c) * (w + l)) / l if l > 0 else 0.0
    out = dict(dist)
    out["full_win"] = dist["full_win"] * scale_w
    out["half_win"] = dist["half_win"] * scale_w
    out["full_lose"] = dist["full_lose"] * scale_l
    out["half_lose"] = dist["half_lose"] * scale_l
    return out


# ---------- selection scanning ----------

def scan_1x2_like(name, model, decimals, cfg, labels):
    market_p = novig_power(decimals)
    blended = blend_probs(model, market_p, cfg["blend"])
    rows = []
    for i, label in enumerate(labels):
        d = decimals[i]
        ev = ev_binary(blended[i], d)
        rows.append({
            "market": name, "selection": label, "odds_decimal": round(d, 3),
            "model_prob": round(model[i], 4),
            "market_prob_novig": round(market_p[i], 4),
            "blended_prob": round(blended[i], 4),
            "ev": round(ev, 4),
            "kelly": round(kelly_binary(blended[i], d), 4),
        })
    return rows


def scan_ah(predict_data, entry, cfg):
    line = entry["line"]
    fmt = entry.get("format") or cfg.get("odds_format")
    (d_home, d_away), _ = convert_all([entry["home"], entry["away"]], fmt)
    q_home, q_away = novig_power([d_home, d_away])
    rows = []
    for side, d, q in (("home", d_home, q_home), ("away", d_away, q_away)):
        side_line = line if side == "home" else -line
        table = predict_data["asian_handicap"][side]
        match = [r for r in table if abs(r["line"] - side_line) < 1e-9]
        if not match:
            continue
        dist = blend_ah_dist(match[0], q, cfg["blend"])
        ev = ev_ah(dist, d)
        rows.append({
            "market": "asian_handicap",
            "selection": f"{side} {side_line:+.2f}",
            "odds_decimal": round(d, 3),
            "model_prob": round(match[0]["win_any"], 4),
            "market_prob_novig": round(q, 4),
            "blended_prob": round(dist["full_win"] + dist["half_win"], 4),
            "ev": round(ev, 4),
            "kelly": round(kelly_ah(dist, d), 4),
        })
    return rows


def scan_double_chance(predict_data, dc_odds, cfg):
    """Double-chance selections (1X/12/X2). The three covers overlap, so there
    is no clean cross-selection no-vig — compare the model cover probability
    against the raw implied for each offered price."""
    model = predict_data.get("double_chance") or {}
    labels = list(dc_odds.keys())
    if not labels:
        return []
    decimals, _ = convert_all(list(dc_odds.values()),
                              cfg.get("odds_format") or "decimal")
    rows = []
    for label, d in zip(labels, decimals):
        p_model = model.get(label)
        if p_model is None:
            continue
        q = min(1.0 / d, 0.999)
        p = cfg["blend"] * p_model + (1.0 - cfg["blend"]) * q
        rows.append({
            "market": "double_chance", "selection": label,
            "odds_decimal": round(d, 3), "model_prob": round(p_model, 4),
            "market_prob_novig": round(q, 4), "blended_prob": round(p, 4),
            "ev": round(ev_binary(p, d), 4),
            "kelly": round(kelly_binary(p, d), 4),
        })
    return rows


def scan_scores(predict_data, score_odds, cfg):
    model = {s["score"]: s["prob"] for s in predict_data["top_scores"]}
    matrix = predict_data.get("score_matrix")
    labels, raws = list(score_odds.keys()), list(score_odds.values())
    decimals, _ = convert_all(raws, cfg.get("odds_format") or "decimal")
    booksum = sum(1.0 / d for d in decimals)
    complete = booksum >= 1.0
    market_p = (novig_power(decimals) if complete
                else [1.0 / d for d in decimals])
    rows = []
    for label, d, q in zip(labels, decimals, market_p):
        p_model = model.get(label)
        if p_model is None and matrix:
            try:
                x, y = (int(v) for v in label.replace(":", "-").split("-"))
                p_model = matrix[x][y] if x < len(matrix) and y < len(matrix) \
                    else 0.0
            except (ValueError, IndexError):
                continue
        if p_model is None:
            continue
        p = cfg["blend"] * p_model + (1.0 - cfg["blend"]) * q
        rows.append({
            "market": "correct_score", "selection": label,
            "odds_decimal": round(d, 3), "model_prob": round(p_model, 4),
            "market_prob_novig": round(q, 4), "blended_prob": round(p, 4),
            "ev": round(ev_binary(p, d), 4),
            "kelly": round(kelly_binary(p, d), 4),
            "note": None if complete else "incomplete score set — raw implied",
        })
    return rows


def build_confidence_picks(rows, cfg):
    """Confidence-gated value (the default objective).

    The goal is guessing right, not chasing EV. Two-step:
    1. Keep result-market selections whose blended probability clears the floor
       (the controllable-risk zone) — this drops the low-probability longshots
       that pure EV ranking would surface.
    2. Rank the survivors by EV, so that among picks you are equally confident
       in, the better-priced one comes first. Hit-rate first, price second.

    Scorelines are listed separately, ranked by probability with a combined
    coverage figure, because even the likeliest scoreline sits below the
    result-market floor — the user still wants the top 2-3 to guess from.
    """
    floor = cfg.get("min_confidence", DEFAULT_MIN_CONFIDENCE)
    result_rows = [r for r in rows if r["market"] != "correct_score"]
    safe = [r for r in result_rows if r["blended_prob"] >= floor]
    safe.sort(key=lambda r: (r["ev"], r["blended_prob"]), reverse=True)
    scores = [r for r in rows if r["market"] == "correct_score"]
    scores.sort(key=lambda r: r["model_prob"], reverse=True)
    top = scores[:3]
    return {
        "floor": floor,
        "safe_picks": safe,
        "scoreline_picks": top,
        "scoreline_coverage": round(sum(r["model_prob"] for r in top), 4),
    }


def build_plan(rows, cfg):
    """Filter to +EV selections and size stakes with fractional Kelly."""
    qualifying = []
    for r in rows:
        threshold = cfg["ev_threshold"] * (2.0 if r["odds_decimal"]
                                           > LONGSHOT_ODDS else 1.0)
        if r["ev"] > threshold:
            stake = min(r["kelly"] * cfg["kelly_fraction"],
                        cfg["max_stake_pct"] / 100.0)
            qualifying.append({**r, "stake_pct": round(stake * 100, 2)})
    qualifying.sort(key=lambda r: r["ev"], reverse=True)
    total = sum(r["stake_pct"] for r in qualifying) / 100.0
    if total > PORTFOLIO_TOTAL_CAP:
        scale = PORTFOLIO_TOTAL_CAP / total
        for r in qualifying:
            r["stake_pct"] = round(r["stake_pct"] * scale, 2)
    return qualifying


# ---------- parlay mode ----------

def filter_legs(legs, cfg):
    eligible, excluded = [], []
    for leg in legs:
        d, _ = convert_all([leg["odds"]], cfg.get("odds_format") or "decimal")
        leg = {**leg, "odds_decimal": d[0]}
        reasons = []
        if str(leg.get("confidence", "B")).upper() == "C":
            reasons.append("confidence C — 拿不准的场次不进串")
        if leg["prob"] < cfg["min_leg_prob"]:
            reasons.append(f"prob {leg['prob']:.2f} < "
                           f"{cfg['min_leg_prob']:.2f} threshold")
        if ev_binary(leg["prob"], leg["odds_decimal"]) <= 0:
            reasons.append("single-leg EV <= 0")
        if reasons:
            excluded.append({**leg, "reasons": reasons})
        else:
            eligible.append(leg)
    return eligible, excluded


def combo_stats(legs):
    odds = 1.0
    prob = 1.0
    for leg in legs:
        odds *= leg["odds_decimal"]
        prob *= leg["prob"]
    return {"legs": [f"{l['match']}: {l['selection']}" for l in legs],
            "size": len(legs), "odds": round(odds, 3),
            "hit_prob": round(prob, 4),
            "ev": round(ev_binary(prob, odds), 4),
            "kelly": round(kelly_binary(prob, odds), 4)}


def parlay_packages(eligible, formats):
    """N串M packages: e.g. '4x11' = every subset of size 2..4 of 4 legs."""
    packages = []
    for spec in formats:
        try:
            n, m = (int(v) for v in spec.lower().split("x"))
        except ValueError:
            raise SystemExit(f"error: bad --parlay-formats entry {spec!r}, "
                             "expected like '3x1' or '4x11'")
        if n > len(eligible):
            packages.append({"format": f"{n}串{m}",
                             "note": f"only {len(eligible)} eligible legs"})
            continue
        legs = eligible[:n]
        min_size = n if m == 1 else 2
        subsets = [c for size in range(min_size, n + 1)
                   for c in itertools.combinations(legs, size)]
        if m != 1 and len(subsets) != m:
            packages.append({"format": f"{n}串{m}",
                             "note": f"{n} legs give {len(subsets)} combos, "
                                     f"not {m} — check the format"})
            continue
        total_ev = sum(combo_stats(list(c))["ev"] for c in subsets)
        packages.append({
            "format": f"{n}串{m}", "n_combos": len(subsets),
            "unit_stakes": len(subsets),
            "package_ev_per_unit": round(total_ev / len(subsets), 4),
            "all_hit_prob": round(math.prod(l["prob"] for l in legs), 4),
        })
    return packages


def run_parlay(legs, cfg):
    eligible, excluded = filter_legs(legs, cfg)
    eligible.sort(key=lambda l: ev_binary(l["prob"], l["odds_decimal"]),
                  reverse=True)
    combos = []
    max_size = min(cfg["parlay_max_size"], len(eligible))
    for size in range(2, max_size + 1):
        combos += [combo_stats(list(c))
                   for c in itertools.combinations(eligible, size)]
    combos.sort(key=lambda c: c["ev"], reverse=True)
    return {
        "eligible_legs": [{k: v for k, v in l.items()} for l in eligible],
        "excluded_legs": excluded,
        "combos": combos[:20],
        "recommended": combos[0] if combos else None,
        "packages": parlay_packages(eligible, cfg["parlay_formats"]),
        "assumptions": "cross-match independence assumed; parlay variance "
                       "rises steeply with leg count",
    }


# ---------- portfolio mode ----------

def run_portfolio(predict_data, odds_data, cfg):
    rows = []
    fmt = odds_data.get("format") or cfg.get("odds_format")
    cfg = {**cfg, "odds_format": fmt}
    if "one_x_two" in odds_data:
        decimals, _ = convert_all(odds_data["one_x_two"], fmt)
        model = [predict_data["one_x_two"][k] for k in ("home", "draw", "away")]
        rows += scan_1x2_like("1x2", model, decimals,
                              cfg, ["home", "draw", "away"])
    for entry in odds_data.get("asian_handicap", []):
        rows += scan_ah(predict_data, entry, cfg)
    for entry in odds_data.get("csl", []):
        h = entry["handicap"]
        match = [r for r in predict_data["csl_handicap"]
                 if r["handicap"] == h]
        if not match:
            continue
        decimals, _ = convert_all(entry["odds"], fmt)
        model = [match[0][k] for k in ("home", "draw", "away")]
        rows += scan_1x2_like(f"csl {h:+d}", model, decimals, cfg,
                              [f"home {h:+d}", f"draw {h:+d}",
                               f"away {h:+d}"])
    if "double_chance" in odds_data:
        rows += scan_double_chance(predict_data, odds_data["double_chance"], cfg)
    if "correct_score" in odds_data:
        rows += scan_scores(predict_data, odds_data["correct_score"], cfg)
    rows.sort(key=lambda r: r["ev"], reverse=True)
    plan = build_plan(rows, cfg)
    picks = build_confidence_picks(rows, cfg)
    top = picks["safe_picks"][0] if picks["safe_picks"] else None
    return {
        "objective": cfg.get("objective", "confidence"),
        "all_selections": rows,
        "confidence_picks": picks,
        "plan": plan,
        "verdict": (
            f"最高把握优选: {top['market']} {top['selection']} "
            f"(命中概率 {top['blended_prob']:.0%}, 赔率 {top['odds_decimal']})"
            if top else
            "无选项达到置信下限, 仅给出最可能比分参考"),
        "ev_verdict": ("VALUE FOUND" if plan else
                       "NO VALUE — market pricing is fair, 建议观望"),
    }


# ---------- output ----------

def confidence_markdown(result, budget):
    """Hit-rate-first output: most-likely scorelines + safe result picks
    ranked by value within the confidence floor. EV plan is demoted to a
    secondary reference, not the headline."""
    picks = result["confidence_picks"]
    lines = ["### High-confidence picks (value.py v%s)" % VALUE_VERSION, "",
             f"**{result['verdict']}**", ""]
    if picks["scoreline_picks"]:
        lines += [f"**Most-likely scorelines** (top {len(picks['scoreline_picks'])} "
                  f"cover ~{picks['scoreline_coverage']:.1%}):", "",
                  "| Score | Model prob | Odds |", "|---|---|---|"]
        for r in picks["scoreline_picks"]:
            lines.append(f"| {r['selection']} | {r['model_prob']:.1%} | "
                         f"{r['odds_decimal']} |")
        lines.append("")
    if picks["safe_picks"]:
        lines += [f"**Safe result picks** (model prob >= {picks['floor']:.0%}, "
                  "better price first):", "",
                  "| Market | Selection | Odds | Model | Blend | EV |",
                  "|---|---|---|---|---|---|"]
        for r in picks["safe_picks"][:8]:
            lines.append(f"| {r['market']} | {r['selection']} | "
                         f"{r['odds_decimal']} | {r['model_prob']:.1%} | "
                         f"{r['blended_prob']:.1%} | {r['ev']:+.2%} |")
        lines += ["", "Within the confidence floor, higher-odds picks rank "
                      "first — hit-rate first, better price second."]
    else:
        lines += [f"No selection cleared the {picks['floor']:.0%} confidence "
                  "floor. Use the most-likely scorelines above, or lower "
                  "--min-confidence."]
    lines += ["", "_EV reference (secondary — not the headline objective):_"]
    for r in result["all_selections"][:3]:
        lines.append(f"- {r['market']} {r['selection']} @ {r['odds_decimal']}: "
                     f"EV {r['ev']:+.2%}, model {r['model_prob']:.1%}")
    lines += ["", DISCLAIMER]
    return "\n".join(lines)


def plan_markdown(result, budget):
    lines = ["### Value scan (value.py v%s)" % VALUE_VERSION, "",
             "| Market | Selection | Odds | Model | Market | Blend | EV | "
             "Kelly |", "|---|---|---|---|---|---|---|---|"]
    for r in result["all_selections"][:15]:
        lines.append(f"| {r['market']} | {r['selection']} | "
                     f"{r['odds_decimal']} | {r['model_prob']:.1%} | "
                     f"{r['market_prob_novig']:.1%} | "
                     f"{r['blended_prob']:.1%} | {r['ev']:+.2%} | "
                     f"{r['kelly']:.3f} |")
    lines += ["", f"**{result.get('ev_verdict', result['verdict'])}**", ""]
    if result["plan"]:
        lines += ["| Pick | Odds | EV | Stake %bankroll" +
                  (f" | Stake ({budget}) |" if budget else " |"),
                  "|---|---|---|---|" + ("---|" if budget else "")]
        for r in result["plan"]:
            row = (f"| {r['market']} {r['selection']} | {r['odds_decimal']} "
                   f"| {r['ev']:+.2%} | {r['stake_pct']}% |")
            if budget:
                row += f" {budget * r['stake_pct'] / 100:.1f} |"
            lines.append(row)
        lines += ["", "Same-match selections are correlated — treat the "
                      "top pick as primary."]
    lines += ["", DISCLAIMER]
    return "\n".join(lines)


def parlay_markdown(result):
    lines = ["### Parlay builder (value.py v%s)" % VALUE_VERSION, ""]
    if result["excluded_legs"]:
        lines += ["**Excluded legs (拿不准的场次已剔除):**", ""]
        for leg in result["excluded_legs"]:
            lines.append(f"- {leg['match']}: {leg['selection']} — "
                         + "; ".join(leg["reasons"]))
        lines.append("")
    if not result["combos"]:
        lines += ["No eligible parlay (fewer than 2 qualifying legs).", ""]
    else:
        lines += ["| Combo | Odds | Hit prob | EV | Kelly |",
                  "|---|---|---|---|---|"]
        for c in result["combos"][:10]:
            lines.append(f"| {' + '.join(c['legs'])} | {c['odds']} | "
                         f"{c['hit_prob']:.1%} | {c['ev']:+.2%} | "
                         f"{c['kelly']:.3f} |")
        rec = result["recommended"]
        lines += ["", f"**Recommended: {' + '.join(rec['legs'])}** "
                      f"(odds {rec['odds']}, hit {rec['hit_prob']:.1%}, "
                      f"EV {rec['ev']:+.2%})"]
    for p in result["packages"]:
        note = p.get("note")
        lines.append(f"- {p['format']}: " + (note if note else
                     f"{p['n_combos']} combos, EV/unit "
                     f"{p['package_ev_per_unit']:+.2%}, all-hit "
                     f"{p['all_hit_prob']:.1%}"))
    lines += ["", result["assumptions"], "", DISCLAIMER]
    return "\n".join(lines)


# ---------- CLI ----------

def parse_probs(spec):
    probs = [float(v) for v in spec.split(",")]
    if abs(sum(probs) - 1.0) > 0.02:
        raise SystemExit(f"error: probabilities {probs} sum to "
                         f"{sum(probs):.3f}, expected ~1.0")
    return probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--predict-json", help="output of predict.py")
    ap.add_argument("--odds-json", help="all priced markets (portfolio mode)")
    ap.add_argument("--parlay", help="legs JSON file (parlay mode)")
    ap.add_argument("--market", choices=("1x2", "csl", "score"))
    ap.add_argument("--odds", help="single-market odds, comma separated")
    ap.add_argument("--model-probs", help="e.g. '0.52,0.26,0.22'")
    ap.add_argument("--odds-format",
                    choices=("decimal", "hk", "malay", "indo"))
    ap.add_argument("--vig-method", choices=("power", "proportional", "both"),
                    default="both")
    ap.add_argument("--objective", choices=("confidence", "ev"),
                    default="confidence",
                    help="confidence: hit-rate-first within a probability "
                         "floor (default). ev: legacy max-EV value plan.")
    ap.add_argument("--min-confidence", type=float,
                    default=DEFAULT_MIN_CONFIDENCE,
                    help="probability floor for confidence picks (default "
                         "0.55)")
    ap.add_argument("--blend", type=float, default=0.65)
    ap.add_argument("--kelly-fraction", type=float, default=0.25)
    ap.add_argument("--ev-threshold", type=float, default=0.02)
    ap.add_argument("--max-stake-pct", type=float, default=2.0)
    ap.add_argument("--budget", type=float)
    ap.add_argument("--min-leg-prob", type=float, default=DEFAULT_MIN_LEG_PROB)
    ap.add_argument("--parlay-max-size", type=int, default=4)
    ap.add_argument("--parlay-formats", default="",
                    help="comma list like '3x1,4x11'")
    ap.add_argument("--format", choices=("json", "markdown", "both"),
                    default="both")
    args = ap.parse_args(argv)

    cfg = {"blend": args.blend, "kelly_fraction": args.kelly_fraction,
           "ev_threshold": args.ev_threshold,
           "max_stake_pct": args.max_stake_pct,
           "odds_format": args.odds_format,
           "objective": args.objective,
           "min_confidence": args.min_confidence,
           "min_leg_prob": args.min_leg_prob,
           "parlay_max_size": args.parlay_max_size,
           "parlay_formats": [f for f in args.parlay_formats.split(",") if f]}

    def portfolio_md(res):
        return (confidence_markdown(res, args.budget)
                if args.objective == "confidence"
                else plan_markdown(res, args.budget))

    if args.parlay:
        with open(args.parlay, encoding="utf-8") as fh:
            result = run_parlay(json.load(fh), cfg)
        md = parlay_markdown(result)
    elif args.odds_json:
        if not args.predict_json:
            raise SystemExit("error: portfolio mode needs --predict-json")
        with open(args.predict_json, encoding="utf-8") as fh:
            predict_data = json.load(fh)
        with open(args.odds_json, encoding="utf-8") as fh:
            odds_data = json.load(fh)
        result = run_portfolio(predict_data, odds_data, cfg)
        md = portfolio_md(result)
    elif args.market:
        if not args.odds:
            raise SystemExit("error: single-market mode needs --odds")
        if args.market == "score":
            pairs = dict(p.split(":") for p in args.odds.split(","))
            odds_data = {"correct_score":
                         {k: float(v) for k, v in pairs.items()}}
        else:
            values = [float(v) for v in args.odds.split(",")]
            key = "one_x_two" if args.market == "1x2" else "csl"
            odds_data = ({"one_x_two": values} if args.market == "1x2"
                         else {"csl": [{"handicap": 0, "odds": values}]})
        if args.predict_json:
            with open(args.predict_json, encoding="utf-8") as fh:
                predict_data = json.load(fh)
        elif args.model_probs and args.market in ("1x2", "csl"):
            probs = parse_probs(args.model_probs)
            predict_data = {
                "one_x_two": dict(zip(("home", "draw", "away"), probs)),
                "csl_handicap": [{"handicap": 0,
                                  **dict(zip(("home", "draw", "away"),
                                             probs))}],
                "top_scores": [], "score_matrix": None}
        else:
            raise SystemExit("error: need --predict-json or --model-probs")
        result = run_portfolio(predict_data, odds_data, cfg)
        md = portfolio_md(result)
    else:
        raise SystemExit("error: pick a mode — --odds-json, --parlay, "
                         "or --market")

    result["meta"] = {"generated_by": f"value.py v{VALUE_VERSION}",
                      "disclaimer": DISCLAIMER}
    if args.format in ("markdown", "both"):
        print(md)
    if args.format == "both":
        print("\n```json")
    if args.format in ("json", "both"):
        print(json.dumps(result, ensure_ascii=False))
    if args.format == "both":
        print("```")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Dixon-Coles Poisson engine: expected goals -> full market probabilities.

Given expected goals (lambda) for both teams, computes the score matrix and
derives every market this skill covers: 1X2, Asian handicap (quarter-ball
settlement), China Sports Lottery integer handicap, and top scorelines.

Stdlib only by design — the skill must run anywhere Python 3.8+ exists.
All betting-market arithmetic lives here so the LLM never does it mentally.
"""

import argparse
import json
import math
import sys

PREDICT_VERSION = "1.0.0"

LAMBDA_HARD_MIN, LAMBDA_HARD_MAX = 0.1, 6.0
LAMBDA_WARN_MIN, LAMBDA_WARN_MAX = 0.5, 3.5
RHO_ABS_CAP = 0.35
TAIL_MASS_LIMIT = 1e-6
MAX_GOALS_CAP = 15
# Style reweighting: fraction of source-region mass moved between blowout
# (margin >= 3) and narrow-win (margin 1-2) cells. Asymmetric because narrow
# wins hold far more mass than blowouts in any realistic matrix.
CONTROLLED_TRANSFER = 0.25   # blowout -> narrow
RUTHLESS_TRANSFER = 0.15     # narrow -> blowout
BLOWOUT_MARGIN = 3

STYLES = ("balanced", "controlled", "ruthless")


def poisson_pmf(lam, n_max):
    """P(X=k) for k in 0..n_max, computed iteratively to avoid factorials."""
    probs = [math.exp(-lam)]
    for k in range(1, n_max + 1):
        probs.append(probs[-1] * lam / k)
    return probs


def dc_tau(x, y, lam, mu, rho):
    """Dixon-Coles low-score correction factor."""
    if x == 0 and y == 0:
        return 1.0 - lam * mu * rho
    if x == 0 and y == 1:
        return 1.0 + lam * rho
    if x == 1 and y == 0:
        return 1.0 + mu * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def clamp_rho(rho, lam, mu):
    """Clamp rho to the region where all tau factors stay non-negative."""
    lo = max(-1.0 / lam if lam > 0 else -RHO_ABS_CAP,
             -1.0 / mu if mu > 0 else -RHO_ABS_CAP,
             -RHO_ABS_CAP)
    hi = min(1.0 / (lam * mu) if lam * mu > 0 else RHO_ABS_CAP,
             1.0,
             RHO_ABS_CAP)
    clamped = min(max(rho, lo), hi)
    return clamped, clamped != rho


def build_matrix(lam, mu, rho, max_goals=None):
    """Score probability matrix P[x][y], truncated and renormalized.

    max_goals is raised automatically until the truncated tail mass is
    negligible, so lopsided lambdas cannot silently lose probability.
    """
    n = max_goals if max_goals is not None else 10
    while True:
        ph = poisson_pmf(lam, n)
        pa = poisson_pmf(mu, n)
        tail = 1.0 - sum(ph) + 1.0 - sum(pa)
        if tail < TAIL_MASS_LIMIT or n >= MAX_GOALS_CAP:
            break
        n += 1
    matrix = [[ph[x] * pa[y] * dc_tau(x, y, lam, mu, rho)
               for y in range(n + 1)] for x in range(n + 1)]
    total = sum(sum(row) for row in matrix)
    return [[cell / total for cell in row] for row in matrix], n


def apply_style(matrix, style, is_home):
    """Reshape scoreline distribution for one team's winning region.

    Moves mass between blowout wins (margin >= 3) and narrow wins (margin 1-2)
    within the same team's win region only, so 1X2 probabilities are invariant.
    'controlled' teams shut games down when ahead; 'ruthless' teams keep
    scoring. Redistribution is proportional to existing target-cell mass.
    """
    if style == "balanced":
        return matrix
    n = len(matrix) - 1
    margin = (lambda x, y: x - y) if is_home else (lambda x, y: y - x)
    blowout, narrow = [], []
    for x in range(n + 1):
        for y in range(n + 1):
            m = margin(x, y)
            if m >= BLOWOUT_MARGIN:
                blowout.append((x, y))
            elif 1 <= m < BLOWOUT_MARGIN:
                narrow.append((x, y))
    src, dst, frac = ((blowout, narrow, CONTROLLED_TRANSFER)
                      if style == "controlled"
                      else (narrow, blowout, RUTHLESS_TRANSFER))
    src_mass = sum(matrix[x][y] for x, y in src)
    dst_mass = sum(matrix[x][y] for x, y in dst)
    if src_mass <= 0 or dst_mass <= 0:
        return matrix  # nothing to move or nowhere to put it
    moved = src_mass * frac
    out = [row[:] for row in matrix]
    for x, y in src:
        out[x][y] -= matrix[x][y] * frac
    for x, y in dst:
        out[x][y] += moved * (matrix[x][y] / dst_mass)
    return out


def one_x_two(matrix):
    n = len(matrix) - 1
    home = sum(matrix[x][y] for x in range(n + 1) for y in range(n + 1) if x > y)
    draw = sum(matrix[x][x] for x in range(n + 1))
    return {"home": home, "draw": draw, "away": 1.0 - home - draw}


def _settle_single(line, margin):
    """Settle a non-quarter line: returns 'win' | 'push' | 'lose'."""
    adj = margin + line
    if adj > 1e-9:
        return "win"
    if adj < -1e-9:
        return "lose"
    return "push"


def settle_ah(matrix, line, side):
    """Five-way settlement distribution for backing `side` at `line`.

    Quarter lines split the stake across the two adjacent half-lines; the
    combined outcome per cell is full/half win, push, half/full lose.
    """
    n = len(matrix) - 1
    is_quarter = abs(line * 4 - round(line * 4)) < 1e-9 and \
        abs(line * 2 - round(line * 2)) > 1e-9
    dist = {"full_win": 0.0, "half_win": 0.0, "push": 0.0,
            "half_lose": 0.0, "full_lose": 0.0}
    for x in range(n + 1):
        for y in range(n + 1):
            p = matrix[x][y]
            margin = (x - y) if side == "home" else (y - x)
            if is_quarter:
                r1 = _settle_single(line - 0.25, margin)
                r2 = _settle_single(line + 0.25, margin)
                pair = tuple(sorted((r1, r2)))
                key = {("win", "win"): "full_win",
                       ("push", "win"): "half_win",
                       ("push", "push"): "push",
                       ("lose", "push"): "half_lose",
                       ("lose", "lose"): "full_lose",
                       ("lose", "win"): None}[pair]
                if key is None:  # adjacent half-lines can never split win/lose
                    raise AssertionError("impossible quarter settlement")
            else:
                key = {"win": "full_win", "push": "push",
                       "lose": "full_lose"}[_settle_single(line, margin)]
            dist[key] += p
    dist["win_any"] = dist["full_win"] + dist["half_win"]
    dist["lose_any"] = dist["full_lose"] + dist["half_lose"]
    return dist


def csl_handicap(matrix, h):
    """China Sports Lottery 让球胜平负: integer shift keeps a real draw."""
    n = len(matrix) - 1
    res = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for x in range(n + 1):
        for y in range(n + 1):
            adj = x + h
            key = "home" if adj > y else ("draw" if adj == y else "away")
            res[key] += matrix[x][y]
    return res


def top_scores(matrix, k):
    n = len(matrix) - 1
    cells = [(f"{x}-{y}", matrix[x][y])
             for x in range(n + 1) for y in range(n + 1)]
    cells.sort(key=lambda c: c[1], reverse=True)
    return [{"score": s, "prob": p} for s, p in cells[:k]]


def expectations(matrix):
    n = len(matrix) - 1
    eh = sum(x * matrix[x][y] for x in range(n + 1) for y in range(n + 1))
    ea = sum(y * matrix[x][y] for x in range(n + 1) for y in range(n + 1))
    return eh, ea


def parse_ah_lines(spec):
    """Parse '-2.0..2.0:0.25' into a list of lines."""
    try:
        rng, step = spec.split(":")
        lo, hi = rng.split("..")
        lo, hi, step = float(lo), float(hi), float(step)
    except ValueError:
        raise SystemExit(f"error: bad --ah-lines spec {spec!r}, "
                         "expected e.g. '-2.0..2.0:0.25'")
    if step <= 0 or hi < lo:
        raise SystemExit("error: --ah-lines needs step > 0 and end >= start")
    count = int(round((hi - lo) / step))
    return [round(lo + i * step, 2) for i in range(count + 1)]


def compute(lam, mu, rho=0.0, style_home="balanced", style_away="balanced",
            ah_lines=None, csl_h=None, n_top=8, max_goals=None):
    """Full pipeline; returns the result dict (JSON schema of this tool)."""
    if not (LAMBDA_HARD_MIN < lam <= LAMBDA_HARD_MAX
            and LAMBDA_HARD_MIN < mu <= LAMBDA_HARD_MAX):
        raise SystemExit(f"error: lambdas must be in ({LAMBDA_HARD_MIN}, "
                         f"{LAMBDA_HARD_MAX}], got {lam}, {mu}")
    warnings = []
    for name, v in (("home", lam), ("away", mu)):
        if not (LAMBDA_WARN_MIN <= v <= LAMBDA_WARN_MAX):
            warnings.append(f"lambda_{name}={v} outside typical range "
                            f"[{LAMBDA_WARN_MIN}, {LAMBDA_WARN_MAX}] — "
                            "double-check the derivation")
    rho_used, was_clamped = clamp_rho(rho, lam, mu)
    if was_clamped:
        warnings.append(f"rho clamped from {rho} to {rho_used:.4f}")
    matrix, n = build_matrix(lam, mu, rho_used, max_goals)
    matrix = apply_style(matrix, style_home, is_home=True)
    matrix = apply_style(matrix, style_away, is_home=False)
    eh, ea = expectations(matrix)
    oxt = one_x_two(matrix)
    lines = ah_lines if ah_lines is not None else parse_ah_lines("-2.0..2.0:0.25")
    ah = {side: [dict(line=l, **{k: round(v, 6) for k, v in
                                 settle_ah(matrix, l, side).items()})
                 for l in lines]
          for side in ("home", "away")}
    csl_list = [csl_h] if csl_h is not None else [-2, -1, 0, 1, 2]
    csl = [dict(handicap=h, **{k: round(v, 6)
                               for k, v in csl_handicap(matrix, h).items()})
           for h in csl_list]
    return {
        "meta": {"generated_by": f"predict.py v{PREDICT_VERSION}",
                 "warnings": warnings},
        "inputs": {"lambda_home": lam, "lambda_away": mu, "rho": rho_used,
                   "style_home": style_home, "style_away": style_away,
                   "max_goals": n},
        "expected": {"home_goals": round(eh, 4), "away_goals": round(ea, 4),
                     "supremacy": round(eh - ea, 4),
                     "total": round(eh + ea, 4)},
        "one_x_two": {k: round(v, 6) for k, v in oxt.items()},
        "fair_odds": {k: round(1.0 / v, 3) if v > 1e-12 else None
                      for k, v in oxt.items()},
        "asian_handicap": ah,
        "csl_handicap": csl,
        "top_scores": [{"score": s["score"], "prob": round(s["prob"], 6)}
                       for s in top_scores(matrix, n_top)],
        "score_matrix": [[round(c, 6) for c in row] for row in matrix],
    }


def bar(p, width=10):
    filled = int(round(p * width))
    return "█" * filled + "░" * (width - filled)


def to_markdown(res, home_name, away_name):
    o = res["one_x_two"]
    exp = res["expected"]
    lines = [
        f"### {home_name} vs {away_name} — model output "
        f"(predict.py v{PREDICT_VERSION})",
        "",
        f"Expected goals: {exp['home_goals']:.2f} - {exp['away_goals']:.2f}  "
        f"(supremacy {exp['supremacy']:+.2f}, total {exp['total']:.2f})",
        "",
        "| Outcome | Prob | Fair odds | |",
        "|---|---|---|---|",
        f"| {home_name} win | {o['home']:.1%} | "
        f"{res['fair_odds']['home']} | {bar(o['home'])} |",
        f"| Draw | {o['draw']:.1%} | {res['fair_odds']['draw']} | "
        f"{bar(o['draw'])} |",
        f"| {away_name} win | {o['away']:.1%} | "
        f"{res['fair_odds']['away']} | {bar(o['away'])} |",
        "",
        "**Top scorelines**",
        "",
        "| Score | Prob |",
        "|---|---|",
    ]
    lines += [f"| {t['score']} | {t['prob']:.1%} |" for t in res["top_scores"]]
    sup = exp["supremacy"]
    lines += ["", f"**Asian handicap ({home_name} side, lines near fair "
                  f"supremacy {sup:+.2f})**", "",
              "| Line | Win | Half win | Push | Half lose | Lose | P(win any) |",
              "|---|---|---|---|---|---|---|"]
    for row in res["asian_handicap"]["home"]:
        if abs(-row["line"] - sup) <= 1.0:
            lines.append(
                f"| {row['line']:+.2f} | {row['full_win']:.1%} | "
                f"{row['half_win']:.1%} | {row['push']:.1%} | "
                f"{row['half_lose']:.1%} | {row['full_lose']:.1%} | "
                f"{row['win_any']:.1%} |")
    lines += ["", "**CSL 让球胜平负 (handicap applied to home goals)**", "",
              "| Handicap | Home | Draw | Away |", "|---|---|---|---|"]
    for row in res["csl_handicap"]:
        lines.append(f"| {row['handicap']:+d} | {row['home']:.1%} | "
                     f"{row['draw']:.1%} | {row['away']:.1%} |")
    for w in res["meta"]["warnings"]:
        lines += ["", f"WARNING: {w}"]
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--home-lambda", type=float, required=True)
    ap.add_argument("--away-lambda", type=float, required=True)
    ap.add_argument("--rho", type=float, default=-0.10,
                    help="Dixon-Coles low-score correlation (default -0.10)")
    ap.add_argument("--style-home", choices=STYLES, default="balanced")
    ap.add_argument("--style-away", choices=STYLES, default="balanced")
    ap.add_argument("--ah-lines", default="-2.0..2.0:0.25")
    ap.add_argument("--csl-handicap", type=int, default=None)
    ap.add_argument("--top-scores", type=int, default=8)
    ap.add_argument("--max-goals", type=int, default=None)
    ap.add_argument("--home-name", default="Home")
    ap.add_argument("--away-name", default="Away")
    ap.add_argument("--format", choices=("json", "markdown", "both"),
                    default="both")
    args = ap.parse_args(argv)

    res = compute(args.home_lambda, args.away_lambda, rho=args.rho,
                  style_home=args.style_home, style_away=args.style_away,
                  ah_lines=parse_ah_lines(args.ah_lines),
                  csl_h=args.csl_handicap, n_top=args.top_scores,
                  max_goals=args.max_goals)
    res["meta"]["home"] = args.home_name
    res["meta"]["away"] = args.away_name

    if args.format in ("markdown", "both"):
        print(to_markdown(res, args.home_name, args.away_name))
    if args.format == "both":
        print("\n```json")
    if args.format in ("json", "both"):
        slim = {k: v for k, v in res.items() if k != "score_matrix"}
        print(json.dumps(res if args.format == "json" else slim,
                         ensure_ascii=False, indent=None))
    if args.format == "both":
        print("```")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Tests for predict.py — the deterministic probability engine.

The Asian-handicap settlement tests use an independent reference
implementation plus hand-written golden cases, so a bug in the script's
settlement logic cannot be masked by testing it against itself.
"""

import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                       / "skills" / "football-predictor" / "scripts"))

import predict  # noqa: E402


# ---------- Poisson / matrix fundamentals ----------

def test_poisson_pmf_matches_closed_form():
    lam = 1.7
    probs = predict.poisson_pmf(lam, 12)
    for k in range(13):
        expected = math.exp(-lam) * lam ** k / math.factorial(k)
        assert probs[k] == pytest.approx(expected, rel=1e-12)


def test_matrix_sums_to_one():
    for lam, mu, rho in [(1.5, 1.2, -0.1), (3.4, 0.4, 0.0), (0.6, 0.6, -0.3)]:
        matrix, _ = predict.build_matrix(lam, mu, rho)
        assert sum(sum(r) for r in matrix) == pytest.approx(1.0, abs=1e-12)


def test_rho_zero_equals_independent_poisson():
    lam, mu = 1.4, 1.1
    matrix, n = predict.build_matrix(lam, mu, 0.0)
    ph = predict.poisson_pmf(lam, n)
    pa = predict.poisson_pmf(mu, n)
    total = sum(ph) * sum(pa)
    for x in range(n + 1):
        for y in range(n + 1):
            assert matrix[x][y] == pytest.approx(ph[x] * pa[y] / total,
                                                 rel=1e-9)


def test_negative_rho_inflates_low_draws():
    lam, mu = 1.4, 1.1
    indep, _ = predict.build_matrix(lam, mu, 0.0)
    dc, _ = predict.build_matrix(lam, mu, -0.15)
    assert dc[0][0] > indep[0][0]
    assert dc[1][1] > indep[1][1]
    assert dc[1][0] < indep[1][0]
    assert dc[0][1] < indep[0][1]


def test_rho_clamped_to_validity_region():
    clamped, was = predict.clamp_rho(-5.0, 1.5, 1.2)
    assert was
    for (x, y) in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        assert predict.dc_tau(x, y, 1.5, 1.2, clamped) >= 0


def test_lopsided_lambdas_keep_tail_mass():
    matrix, n = predict.build_matrix(3.5, 0.4, -0.1)
    assert n > 10  # auto-raised
    assert sum(sum(r) for r in matrix) == pytest.approx(1.0, abs=1e-12)


def test_expected_goals_track_lambdas():
    matrix, _ = predict.build_matrix(1.8, 1.1, 0.0)
    eh, ea = predict.expectations(matrix)
    assert eh == pytest.approx(1.8, abs=1e-3)
    assert ea == pytest.approx(1.1, abs=1e-3)


# ---------- style reweighting ----------

def _blowout_mass(matrix, is_home):
    n = len(matrix) - 1
    return sum(matrix[x][y] for x in range(n + 1) for y in range(n + 1)
               if ((x - y) if is_home else (y - x)) >= predict.BLOWOUT_MARGIN)


@pytest.mark.parametrize("style", ["controlled", "ruthless"])
def test_style_preserves_one_x_two_and_mass(style):
    base, _ = predict.build_matrix(1.9, 1.0, -0.1)
    styled = predict.apply_style(base, style, is_home=True)
    assert sum(sum(r) for r in styled) == pytest.approx(1.0, abs=1e-9)
    for key, val in predict.one_x_two(base).items():
        assert predict.one_x_two(styled)[key] == pytest.approx(val, abs=1e-9)


def test_controlled_shrinks_blowouts_ruthless_grows_them():
    base, _ = predict.build_matrix(1.9, 1.0, -0.1)
    controlled = predict.apply_style(base, "controlled", is_home=True)
    ruthless = predict.apply_style(base, "ruthless", is_home=True)
    assert _blowout_mass(controlled, True) < _blowout_mass(base, True)
    assert _blowout_mass(ruthless, True) > _blowout_mass(base, True)


def test_balanced_is_identity():
    base, _ = predict.build_matrix(1.5, 1.2, -0.1)
    assert predict.apply_style(base, "balanced", True) is base


def test_away_style_only_touches_away_wins():
    base, _ = predict.build_matrix(1.5, 1.2, -0.1)
    styled = predict.apply_style(base, "controlled", is_home=False)
    n = len(base) - 1
    for x in range(n + 1):
        for y in range(n + 1):
            if y <= x:  # home wins and draws untouched
                assert styled[x][y] == pytest.approx(base[x][y], abs=1e-15)


# ---------- Asian handicap settlement ----------

def _delta_matrix(hx, hy, n=8):
    """All probability mass on a single scoreline hx-hy."""
    m = [[0.0] * (n + 1) for _ in range(n + 1)]
    m[hx][hy] = 1.0
    return m


def _reference_settle(line, margin):
    """Independent reference: settle each half-stake, count results."""
    quarter = (line * 4) == round(line * 4) and (line * 2) != round(line * 2)
    subs = [line - 0.25, line + 0.25] if quarter else [line, line]
    results = []
    for sub in subs:
        adj = margin + sub
        results.append("w" if adj > 1e-9 else ("l" if adj < -1e-9 else "p"))
    wins, pushes = results.count("w"), results.count("p")
    if wins == 2:
        return "full_win"
    if wins == 1 and pushes == 1:
        return "half_win"
    if pushes == 2:
        return "push"
    if pushes == 1:
        return "half_lose"
    if wins == 1:
        raise AssertionError("win+lose split impossible on adjacent lines")
    return "full_lose"


def test_ah_settlement_full_enumeration():
    """Every quarter-step line in [-2, 2] x every margin in [-4, 4]."""
    lines = [round(-2 + i * 0.25, 2) for i in range(17)]
    for line in lines:
        for margin in range(-4, 5):
            hx, hy = (margin + 4, 4)
            dist = predict.settle_ah(_delta_matrix(hx, hy), line, "home")
            expected = _reference_settle(line, margin)
            assert dist[expected] == pytest.approx(1.0), \
                f"line={line} margin={margin}: expected {expected}, got {dist}"


HAND_GOLDEN = [
    # (line, margin, category) — hand-computed classic quarter-ball cases
    (-0.25, 0, "half_lose"),   # 平半盘 draw: lose half
    (0.25, 0, "half_win"),     # 受让平半 draw: win half
    (-0.75, 1, "half_win"),    # 半一盘 win by 1: win half
    (-0.75, 2, "full_win"),
    (-1.25, 1, "half_lose"),   # 一球球半 win by 1: lose half
    (-1.75, 2, "half_win"),
    (0.0, 0, "push"),          # 平手盘 draw: stake returned
    (-1.0, 1, "push"),
    (-0.5, 0, "full_lose"),
    (0.75, -1, "half_lose"),
]


@pytest.mark.parametrize("line,margin,category", HAND_GOLDEN)
def test_ah_hand_golden_cases(line, margin, category):
    dist = predict.settle_ah(_delta_matrix(margin + 4, 4), line, "home")
    assert dist[category] == pytest.approx(1.0)


def test_ah_home_away_complementarity():
    matrix, _ = predict.build_matrix(1.7, 1.1, -0.1)
    for line in [-1.75, -1.0, -0.75, -0.25, 0.0, 0.5, 1.25]:
        home = predict.settle_ah(matrix, line, "home")
        away = predict.settle_ah(matrix, -line, "away")
        assert home["full_win"] == pytest.approx(away["full_lose"], abs=1e-12)
        assert home["half_win"] == pytest.approx(away["half_lose"], abs=1e-12)
        assert home["push"] == pytest.approx(away["push"], abs=1e-12)


def test_ah_distribution_sums_to_one():
    matrix, _ = predict.build_matrix(2.1, 0.8, -0.1)
    for line in [round(-2 + i * 0.25, 2) for i in range(17)]:
        d = predict.settle_ah(matrix, line, "home")
        total = (d["full_win"] + d["half_win"] + d["push"]
                 + d["half_lose"] + d["full_lose"])
        assert total == pytest.approx(1.0, abs=1e-12)


# ---------- CSL handicap ----------

def test_csl_matches_brute_force():
    matrix, n = predict.build_matrix(1.6, 1.2, -0.1)
    for h in (-2, -1, 0, 1, 2):
        res = predict.csl_handicap(matrix, h)
        brute = {"home": 0.0, "draw": 0.0, "away": 0.0}
        for x in range(n + 1):
            for y in range(n + 1):
                key = ("home" if x + h > y else
                       "draw" if x + h == y else "away")
                brute[key] += matrix[x][y]
        for k in brute:
            assert res[k] == pytest.approx(brute[k], abs=1e-12)
        assert sum(res.values()) == pytest.approx(1.0, abs=1e-12)


def test_csl_zero_equals_one_x_two():
    matrix, _ = predict.build_matrix(1.6, 1.2, -0.1)
    assert predict.csl_handicap(matrix, 0) == pytest.approx(
        predict.one_x_two(matrix))


# ---------- validation & CLI ----------

def test_lambda_out_of_range_rejected():
    with pytest.raises(SystemExit):
        predict.compute(0.0, 1.2)
    with pytest.raises(SystemExit):
        predict.compute(1.2, 7.0)


def test_extreme_lambda_warns():
    res = predict.compute(4.5, 1.0)
    assert any("outside typical range" in w for w in res["meta"]["warnings"])


def test_parse_ah_lines():
    lines = predict.parse_ah_lines("-1.0..1.0:0.5")
    assert lines == [-1.0, -0.5, 0.0, 0.5, 1.0]
    with pytest.raises(SystemExit):
        predict.parse_ah_lines("garbage")


def test_top_scores_sorted_and_sized():
    res = predict.compute(1.5, 1.2, n_top=5)
    probs = [t["prob"] for t in res["top_scores"]]
    assert len(probs) == 5
    assert probs == sorted(probs, reverse=True)


def test_cli_json_output_parses(capsys):
    predict.main(["--home-lambda", "1.55", "--away-lambda", "1.03",
                  "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["one_x_two"]["home"] > data["one_x_two"]["away"]
    assert data["meta"]["home"] == "Home"


def test_cli_markdown_no_emoji(capsys):
    predict.main(["--home-lambda", "1.55", "--away-lambda", "1.03",
                  "--home-name", "Arsenal", "--away-name", "Liverpool",
                  "--format", "markdown"])
    out = capsys.readouterr().out
    assert "Arsenal" in out
    assert not any(0x1F300 <= ord(c) <= 0x1FAFF for c in out)

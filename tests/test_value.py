"""Tests for value.py — odds conversion, vig removal, EV, Kelly, parlays."""

import json
import math
import sys
from pathlib import Path

import pytest

SCRIPTS = (Path(__file__).resolve().parents[1]
           / "skills" / "football-predictor" / "scripts")
sys.path.insert(0, str(SCRIPTS))

import predict  # noqa: E402
import value    # noqa: E402


# ---------- odds conversion ----------

@pytest.mark.parametrize("raw,fmt,expected", [
    (2.05, "decimal", 2.05),
    (0.95, "hk", 1.95),
    (0.80, "malay", 1.80),          # positive malay
    (-0.90, "malay", 1 + 1 / 0.90),  # negative malay
    (1.50, "indo", 2.50),           # positive indo
    (-2.00, "indo", 1.50),          # negative indo
])
def test_odds_conversion(raw, fmt, expected):
    assert value.to_decimal(raw, fmt) == pytest.approx(expected)


def test_hk_decimal_roundtrip():
    for hk in (0.75, 0.90, 1.10):
        assert value.to_decimal(hk, "hk") - 1.0 == pytest.approx(hk)


def test_detect_format():
    assert value.detect_format([2.05, 3.60, 3.80]) == "decimal"
    assert value.detect_format([0.95, 0.87]) == "hk"
    assert value.detect_format([-0.90, 0.80]) == "malay"
    with pytest.raises(SystemExit):
        value.detect_format([1.05, 1.10])  # decimal-or-HK ambiguity


def test_bad_odds_rejected():
    with pytest.raises(SystemExit):
        value.to_decimal(0.0, "decimal")


# ---------- vig removal ----------

def test_proportional_novig_sums_to_one():
    probs = value.novig_proportional([2.05, 3.60, 3.80])
    assert sum(probs) == pytest.approx(1.0)


def test_power_novig_sums_to_one_and_shrinks_longshots():
    decimals = [1.30, 5.50, 12.0]
    prop = value.novig_proportional(decimals)
    power = value.novig_power(decimals)
    assert sum(power) == pytest.approx(1.0, abs=1e-8)
    # power method shrinks the longshot more than proportional does
    assert power[2] < prop[2]
    assert power[0] > prop[0]


def test_novig_on_fair_odds_is_identity():
    fair = [2.0, 4.0, 4.0]  # booksum exactly 1
    for method in (value.novig_proportional, value.novig_power):
        probs = method(fair)
        assert probs == pytest.approx([0.5, 0.25, 0.25], abs=1e-6)


# ---------- EV & Kelly ----------

def test_ev_binary_zero_at_fair_odds():
    assert value.ev_binary(0.5, 2.0) == pytest.approx(0.0)
    assert value.ev_binary(0.55, 2.0) == pytest.approx(0.10)


def test_kelly_binary_closed_form():
    assert value.kelly_binary(0.55, 2.0) == pytest.approx(0.10)
    assert value.kelly_binary(0.40, 2.0) == 0.0  # -EV -> no bet


def test_ev_ah_half_win_and_push_cases():
    dist = {"full_win": 0.5, "half_win": 0.2, "push": 0.1,
            "half_lose": 0.1, "full_lose": 0.1}
    d = 1.95
    expected = 0.5 * 0.95 + 0.2 * 0.475 - 0.1 * 0.5 - 0.1
    assert value.ev_ah(dist, d) == pytest.approx(expected)


def test_kelly_ah_matches_binary_when_degenerate():
    """With no half/push outcomes, multi-outcome Kelly = closed form."""
    dist = {"full_win": 0.55, "half_win": 0.0, "push": 0.0,
            "half_lose": 0.0, "full_lose": 0.45}
    f = value.kelly_ah(dist, 2.0)
    assert f == pytest.approx(value.kelly_binary(0.55, 2.0), abs=1e-3)


def test_kelly_ah_zero_for_negative_ev():
    dist = {"full_win": 0.40, "half_win": 0.0, "push": 0.0,
            "half_lose": 0.0, "full_lose": 0.60}
    assert value.kelly_ah(dist, 2.0) == 0.0


def test_blend_ah_dist_pulls_toward_market():
    dist = {"full_win": 0.60, "half_win": 0.0, "push": 0.1,
            "half_lose": 0.0, "full_lose": 0.30}
    blended = value.blend_ah_dist(dist, q_market=0.50, blend=0.65)
    # neutral mass unchanged, decided mass re-split toward market
    assert blended["push"] == pytest.approx(0.1)
    w = blended["full_win"]
    l = blended["full_lose"]
    c_expected = 0.65 * (0.6 / 0.9) + 0.35 * 0.5
    assert w / (w + l) == pytest.approx(c_expected)
    total = sum(blended[k] for k in
                ("full_win", "half_win", "push", "half_lose", "full_lose"))
    assert total == pytest.approx(1.0)


# ---------- double chance scanning ----------

def test_scan_double_chance_uses_model_prob_and_computes_ev():
    predict_data = {"double_chance": {"1X": 0.75, "12": 0.80, "X2": 0.55}}
    dc_odds = {"1X": 1.05, "12": 1.22}
    cfg = {"blend": 0.65, "odds_format": "decimal"}
    rows = value.scan_double_chance(predict_data, dc_odds, cfg)
    assert {r["selection"] for r in rows} == {"1X", "12"}
    row = next(r for r in rows if r["selection"] == "1X")
    assert row["market"] == "double_chance"
    assert row["odds_decimal"] == pytest.approx(1.05)
    assert row["model_prob"] == pytest.approx(0.75)  # taken straight from predict_data
    q = min(1.0 / 1.05, 0.999)
    p = 0.65 * 0.75 + 0.35 * q
    assert row["blended_prob"] == pytest.approx(round(p, 4))
    assert row["ev"] == pytest.approx(round(value.ev_binary(p, 1.05), 4))
    assert row["kelly"] == pytest.approx(round(value.kelly_binary(p, 1.05), 4))


def test_scan_double_chance_skips_labels_missing_from_model():
    predict_data = {"double_chance": {"1X": 0.75, "12": 0.80, "X2": 0.55}}
    # BTTS is not a double-chance label the model produces -> must be skipped
    dc_odds = {"1X": 1.05, "BTTS": 1.90}
    cfg = {"blend": 0.65, "odds_format": "decimal"}
    rows = value.scan_double_chance(predict_data, dc_odds, cfg)
    assert {r["selection"] for r in rows} == {"1X"}


def test_scan_double_chance_empty_odds_returns_no_rows():
    predict_data = {"double_chance": {"1X": 0.75, "12": 0.80, "X2": 0.55}}
    cfg = {"blend": 0.65, "odds_format": "decimal"}
    assert value.scan_double_chance(predict_data, {}, cfg) == []


# ---------- confidence-gated picks ----------

def test_build_confidence_picks_filters_below_floor_and_sorts_by_ev():
    rows = [
        {"market": "1x2", "selection": "home", "blended_prob": 0.60,
         "ev": 0.05, "model_prob": 0.55},
        {"market": "double_chance", "selection": "1X", "blended_prob": 0.80,
         "ev": 0.02, "model_prob": 0.78},
        {"market": "asian_handicap", "selection": "home -0.5",
         "blended_prob": 0.50, "ev": 0.15, "model_prob": 0.48},
        {"market": "correct_score", "selection": "1-0", "blended_prob": 0.10,
         "ev": 0.30, "model_prob": 0.12},
        {"market": "correct_score", "selection": "1-1", "blended_prob": 0.09,
         "ev": 0.10, "model_prob": 0.10},
        {"market": "correct_score", "selection": "2-1", "blended_prob": 0.07,
         "ev": 0.05, "model_prob": 0.08},
        {"market": "correct_score", "selection": "0-0", "blended_prob": 0.06,
         "ev": 0.01, "model_prob": 0.07},
    ]
    picks = value.build_confidence_picks(rows, {"min_confidence": 0.55})
    assert picks["floor"] == 0.55
    safe_selections = [(r["market"], r["selection"]) for r in picks["safe_picks"]]
    # below-floor asian_handicap pick (0.50 < 0.55) is excluded despite high EV
    assert ("asian_handicap", "home -0.5") not in safe_selections
    # correct_score rows never enter safe_picks, regardless of probability
    assert all(r["market"] != "correct_score" for r in picks["safe_picks"])
    # higher-EV survivor (1x2 @ .05) ranks before lower-EV survivor (dc @ .02)
    assert safe_selections == [("1x2", "home"), ("double_chance", "1X")]
    assert [r["ev"] for r in picks["safe_picks"]] == sorted(
        [r["ev"] for r in picks["safe_picks"]], reverse=True)


def test_build_confidence_picks_scoreline_picks_top_three_by_model_prob():
    rows = [
        {"market": "correct_score", "selection": "1-0", "blended_prob": 0.10,
         "ev": 0.30, "model_prob": 0.12},
        {"market": "correct_score", "selection": "1-1", "blended_prob": 0.09,
         "ev": 0.10, "model_prob": 0.10},
        {"market": "correct_score", "selection": "2-1", "blended_prob": 0.07,
         "ev": 0.05, "model_prob": 0.08},
        {"market": "correct_score", "selection": "0-0", "blended_prob": 0.06,
         "ev": 0.01, "model_prob": 0.07},
    ]
    picks = value.build_confidence_picks(rows, {"min_confidence": 0.55})
    assert len(picks["scoreline_picks"]) == 3
    assert [r["selection"] for r in picks["scoreline_picks"]] == \
        ["1-0", "1-1", "2-1"]
    assert picks["scoreline_coverage"] == pytest.approx(
        0.12 + 0.10 + 0.08, abs=1e-4)


def test_build_confidence_picks_uses_default_floor_when_not_configured():
    rows = [{"market": "1x2", "selection": "away", "blended_prob": 0.50,
             "ev": 0.01, "model_prob": 0.50}]
    picks = value.build_confidence_picks(rows, {})
    assert picks["floor"] == value.DEFAULT_MIN_CONFIDENCE
    assert picks["safe_picks"] == []  # 0.50 < default 0.55


# ---------- portfolio mode ----------

def _predict_data():
    return predict.compute(1.55, 1.03, rho=-0.10)


def test_portfolio_finds_value_when_market_misprices():
    cfg = dict(blend=0.65, kelly_fraction=0.25, ev_threshold=0.02,
               max_stake_pct=2.0, odds_format=None)
    # model says home ~52%, market prices home at 45% implied -> value
    odds = {"one_x_two": [2.40, 3.40, 3.30]}
    result = value.run_portfolio(_predict_data(), odds, cfg)
    assert result["plan"], "expected home win flagged as value"
    assert result["plan"][0]["selection"] == "home"
    assert result["ev_verdict"] == "VALUE FOUND"


def test_portfolio_honest_null_when_market_fair():
    data = _predict_data()
    o = data["one_x_two"]
    # price the market exactly at model probabilities plus heavy vig
    odds = {"one_x_two": [round(0.92 / o["home"], 2),
                          round(0.92 / o["draw"], 2),
                          round(0.92 / o["away"], 2)]}
    cfg = dict(blend=0.65, kelly_fraction=0.25, ev_threshold=0.02,
               max_stake_pct=2.0, odds_format=None)
    result = value.run_portfolio(data, odds, cfg)
    assert not result["plan"]
    assert "NO VALUE" in result["ev_verdict"]


def test_portfolio_scans_ah_and_csl_and_scores():
    cfg = dict(blend=0.65, kelly_fraction=0.25, ev_threshold=0.02,
               max_stake_pct=2.0, odds_format=None)
    odds = {
        "one_x_two": [2.05, 3.60, 3.80],
        "asian_handicap": [{"line": -0.25, "home": 0.95, "away": 0.93,
                            "format": "hk"}],
        "csl": [{"handicap": -1, "odds": [3.10, 3.55, 2.05]}],
        "correct_score": {"1-0": 7.5, "2-1": 9.0, "1-1": 6.5},
    }
    result = value.run_portfolio(_predict_data(), odds, cfg)
    markets = {r["market"] for r in result["all_selections"]}
    assert {"1x2", "asian_handicap", "csl -1", "correct_score"} <= markets
    # rows are EV-sorted
    evs = [r["ev"] for r in result["all_selections"]]
    assert evs == sorted(evs, reverse=True)


def _confidence_odds():
    """Short-priced double-chance covers guarantee a safe pick clears the
    default 0.55 confidence floor, unlike the underdog-heavy 1x2 prices used
    elsewhere in this file."""
    return {"one_x_two": [1.60, 4.50, 6.00],
            "double_chance": {"1X": 1.30, "12": 1.35},
            "correct_score": {"1-0": 7.5, "2-1": 9.0, "1-1": 6.5}}


def test_run_portfolio_default_objective_is_confidence():
    cfg = dict(blend=0.65, kelly_fraction=0.25, ev_threshold=0.02,
               max_stake_pct=2.0, odds_format=None)  # no "objective" key
    result = value.run_portfolio(_predict_data(), _confidence_odds(), cfg)
    assert result["objective"] == "confidence"
    assert "confidence_picks" in result
    assert "ev_verdict" in result
    assert "plan" in result


def test_run_portfolio_verdict_leads_with_safest_pick_when_available():
    cfg = dict(blend=0.65, kelly_fraction=0.25, ev_threshold=0.02,
               max_stake_pct=2.0, odds_format=None, min_confidence=0.55)
    result = value.run_portfolio(_predict_data(), _confidence_odds(), cfg)
    assert result["confidence_picks"]["safe_picks"], \
        "expected at least one pick above the confidence floor"
    assert result["verdict"].startswith("最高把握优选")
    top = result["confidence_picks"]["safe_picks"][0]
    assert top["selection"] in result["verdict"]


def test_run_portfolio_verdict_falls_back_when_nothing_clears_floor():
    cfg = dict(blend=0.65, kelly_fraction=0.25, ev_threshold=0.02,
               max_stake_pct=2.0, odds_format=None, min_confidence=0.99)
    result = value.run_portfolio(_predict_data(), _confidence_odds(), cfg)
    assert result["confidence_picks"]["safe_picks"] == []
    assert result["verdict"] == "无选项达到置信下限, 仅给出最可能比分参考"


def test_longshot_threshold_doubles():
    cfg = dict(blend=1.0, kelly_fraction=0.25, ev_threshold=0.02,
               max_stake_pct=2.0, odds_format=None)
    rows = [{"market": "correct_score", "selection": "2-1",
             "odds_decimal": 9.0, "model_prob": 0.115,
             "market_prob_novig": 0.11, "blended_prob": 0.115,
             "ev": 0.03, "kelly": 0.004}]
    # EV 3% passes the base 2% threshold but not the doubled 4% longshot bar
    assert value.build_plan(rows, cfg) == []


def test_stake_caps_apply():
    cfg = dict(blend=1.0, kelly_fraction=0.25, ev_threshold=0.02,
               max_stake_pct=2.0, odds_format=None)
    rows = [{"market": "1x2", "selection": "home", "odds_decimal": 2.0,
             "model_prob": 0.70, "market_prob_novig": 0.5,
             "blended_prob": 0.70, "ev": 0.40, "kelly": 0.40}]
    plan = value.build_plan(rows, cfg)
    assert plan[0]["stake_pct"] == 2.0  # capped, not 10%


def test_confidence_markdown_has_no_emoji_and_expected_sections():
    cfg = dict(blend=0.65, kelly_fraction=0.25, ev_threshold=0.02,
               max_stake_pct=2.0, odds_format=None, min_confidence=0.55)
    result = value.run_portfolio(_predict_data(), _confidence_odds(), cfg)
    md = value.confidence_markdown(result, None)
    assert not any(0x1F300 <= ord(c) <= 0x1FAFF for c in md)
    assert "Most-likely scorelines" in md
    assert "Safe result picks" in md


# ---------- parlay mode ----------

LEGS = [
    {"match": "A vs B", "selection": "home -0.5", "odds": 1.85,
     "prob": 0.62, "confidence": "A"},
    {"match": "C vs D", "selection": "away +0.25", "odds": 1.90,
     "prob": 0.58, "confidence": "B"},
    {"match": "E vs F", "selection": "home", "odds": 2.10,
     "prob": 0.52, "confidence": "C"},   # confidence C -> excluded
    {"match": "G vs H", "selection": "draw", "odds": 3.40,
     "prob": 0.30, "confidence": "A"},   # prob too low -> excluded
]


def _parlay_cfg(**over):
    cfg = dict(blend=0.65, odds_format=None, min_leg_prob=0.55,
               parlay_max_size=4, parlay_formats=[])
    cfg.update(over)
    return cfg


def test_parlay_filters_low_confidence_and_low_prob():
    result = value.run_parlay(LEGS, _parlay_cfg())
    excluded = {l["match"]: l["reasons"] for l in result["excluded_legs"]}
    assert any("confidence C" in r for r in excluded["E vs F"])
    assert any("threshold" in r for r in excluded["G vs H"])
    assert len(result["eligible_legs"]) == 2


def test_parlay_combo_math():
    result = value.run_parlay(LEGS, _parlay_cfg())
    combo = result["recommended"]
    assert combo["size"] == 2
    assert combo["odds"] == pytest.approx(1.85 * 1.90, abs=1e-3)
    assert combo["hit_prob"] == pytest.approx(0.62 * 0.58, abs=1e-4)
    assert combo["ev"] == pytest.approx(
        0.62 * 0.58 * 1.85 * 1.90 - 1, abs=1e-3)


def test_parlay_package_counts():
    legs = [dict(l, confidence="A", prob=0.60) for l in LEGS]
    result = value.run_parlay(legs, _parlay_cfg(parlay_formats=["4x11",
                                                                "3x1"]))
    by_fmt = {p["format"]: p for p in result["packages"]}
    assert by_fmt["4串11"]["n_combos"] == 11  # C(4,2)+C(4,3)+C(4,4)
    assert by_fmt["3串1"]["n_combos"] == 1


def test_parlay_needs_two_legs():
    result = value.run_parlay(LEGS[:1], _parlay_cfg())
    assert result["recommended"] is None


# ---------- CLI integration ----------

def test_cli_pipeline_predict_to_value(tmp_path, capsys):
    predict.main(["--home-lambda", "1.55", "--away-lambda", "1.03",
                  "--format", "json"])
    predict_out = capsys.readouterr().out
    pj = tmp_path / "predict.json"
    pj.write_text(predict_out, encoding="utf-8")
    oj = tmp_path / "odds.json"
    oj.write_text(json.dumps({"one_x_two": [2.40, 3.40, 3.30]}),
                  encoding="utf-8")
    value.main(["--predict-json", str(pj), "--odds-json", str(oj),
                "--format", "json"])
    result = json.loads(capsys.readouterr().out)
    assert result["plan"]
    assert value.DISCLAIMER in result["meta"]["disclaimer"]


def test_cli_single_market_with_model_probs(capsys):
    value.main(["--market", "1x2", "--odds", "2.40,3.40,3.30",
                "--model-probs", "0.52,0.26,0.22", "--format", "json"])
    result = json.loads(capsys.readouterr().out)
    assert result["all_selections"][0]["market"] == "1x2"


def test_cli_parlay_mode(tmp_path, capsys):
    lj = tmp_path / "legs.json"
    lj.write_text(json.dumps(LEGS), encoding="utf-8")
    value.main(["--parlay", str(lj), "--format", "json"])
    result = json.loads(capsys.readouterr().out)
    assert result["recommended"]["size"] == 2
    assert len(result["excluded_legs"]) == 2


def test_markdown_output_no_emoji(tmp_path, capsys):
    lj = tmp_path / "legs.json"
    lj.write_text(json.dumps(LEGS), encoding="utf-8")
    value.main(["--parlay", str(lj), "--format", "markdown"])
    out = capsys.readouterr().out
    assert not any(0x1F300 <= ord(c) <= 0x1FAFF for c in out)

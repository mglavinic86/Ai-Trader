"""Tests for SMC v2 reporting queries in Database."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.database import Database


def _get_test_db() -> Database:
    test_path = Path(__file__).parent / "test_smc_v2_reporting.db"
    if test_path.exists():
        test_path.unlink()
    return Database(test_path)


def test_smc_v2_gate_and_instrument_stats():
    db = _get_test_db()

    db.log_setup_label({
        "instrument": "EUR_USD",
        "direction": "LONG",
        "setup_grade": "A+",
        "confidence": 78,
        "risk_reward": 3.2,
        "allow_trade": 1,
        "within_killzone": 1,
        "news_clear": 1,
        "htf_poi_gate": 1,
        "sweep_valid": 1,
        "fvg_valid": 1,
        "direction_confirmed": 1,
        "choch_or_bos": 1,
        "rr_pass": 1,
        "sl_cap_pass": 1,
        "reason": "ALLOW",
    })
    db.log_setup_label({
        "instrument": "EUR_USD",
        "direction": "SHORT",
        "setup_grade": "A",
        "confidence": 55,
        "risk_reward": 2.3,
        "allow_trade": 0,
        "within_killzone": 0,
        "news_clear": 1,
        "htf_poi_gate": 0,
        "sweep_valid": 1,
        "fvg_valid": 0,
        "direction_confirmed": 1,
        "choch_or_bos": 1,
        "rr_pass": 0,
        "sl_cap_pass": 1,
        "reason": "BLOCK",
    })
    db.log_setup_label({
        "instrument": "XAU_USD",
        "direction": "LONG",
        "setup_grade": "B",
        "confidence": 70,
        "risk_reward": 2.0,
        "allow_trade": 0,
        "within_killzone": 1,
        "news_clear": 0,
        "htf_poi_gate": 1,
        "sweep_valid": 1,
        "fvg_valid": 1,
        "direction_confirmed": 1,
        "choch_or_bos": 1,
        "rr_pass": 0,
        "sl_cap_pass": 0,
        "reason": "BLOCK",
    })

    shadow = db.get_smc_v2_shadow_stats(hours=24)
    assert shadow["total"] == 3
    assert shadow["allow_count"] == 1
    assert shadow["block_count"] == 2

    gates = db.get_smc_v2_gate_stats(hours=24)
    assert "fvg_valid" in gates
    assert gates["fvg_valid"]["total"] == 3
    assert gates["fvg_valid"]["pass_count"] == 2

    by_inst = db.get_smc_v2_by_instrument(hours=24)
    names = {r["instrument"] for r in by_inst}
    assert "EUR_USD" in names
    assert "XAU_USD" in names

    # Cleanup
    test_path = Path(__file__).parent / "test_smc_v2_reporting.db"
    if test_path.exists():
        test_path.unlink()


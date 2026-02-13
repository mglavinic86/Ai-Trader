"""Tests for SMC v2 shadow evaluator logic in MarketScanner."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.auto_config import AutoTradingConfig
from src.smc.smc_analyzer import SMCAnalysis
from src.smc.zones import FairValueGap
from src.smc.displacement import Displacement
from src.trading.auto_scanner import MarketScanner


def _make_scanner_with_cfg(cfg: AutoTradingConfig) -> MarketScanner:
    scanner = MarketScanner.__new__(MarketScanner)
    scanner.config = cfg
    return scanner


def test_strict_fvg_blocks_when_no_valid_fvg():
    cfg = AutoTradingConfig()
    cfg.smc_v2.enabled = True
    cfg.smc_v2.shadow_mode = True
    cfg.smc_v2.strict_fvg.enabled = True

    scanner = _make_scanner_with_cfg(cfg)

    smc = SMCAnalysis(
        setup_grade="A",
        direction="LONG",
        htf_bias="BULLISH",
        current_price=1.1000,
        htf_swing_low=1.0900,
        htf_swing_high=1.1100,
        fvgs=[
            FairValueGap(  # too small relative to ATR
                start_price=1.1002,
                end_price=1.1000,
                direction="BULLISH",
                candle_index=1,
                filled=False,
            )
        ],
        ltf_displacement=Displacement(
            direction="BULLISH",
            candle_index=2,
            body_size=0.0010,
            avg_body_ratio=2.5,
            confirmed=True,
        ),
    )
    technical = SimpleNamespace(atr_pips=10.0)  # ATR price ~= 0.0010

    eval_result = scanner._evaluate_setup_v2(
        instrument="EUR_USD",
        profile={},
        smc_analysis=smc,
        technical=technical,
        confidence=75,
        entry_price=1.1000,
        stop_loss=1.0980,
        risk_reward=3.2,
    )

    assert eval_result.gates["fvg_valid"] is False
    assert eval_result.allow_trade is False


def test_strict_fvg_allows_when_valid_fvg_exists():
    cfg = AutoTradingConfig()
    cfg.smc_v2.enabled = True
    cfg.smc_v2.shadow_mode = True
    cfg.smc_v2.strict_fvg.enabled = True

    scanner = _make_scanner_with_cfg(cfg)

    smc = SMCAnalysis(
        setup_grade="A+",
        direction="LONG",
        htf_bias="BULLISH",
        current_price=1.1000,
        htf_swing_low=1.0900,
        htf_swing_high=1.1100,
        premium_discount={"zone": "DISCOUNT"},
        fvgs=[
            FairValueGap(  # size 0.0016 >= 1.2*ATR(0.0010)
                start_price=1.1016,
                end_price=1.1000,
                direction="BULLISH",
                candle_index=1,
                filled=False,
            )
        ],
        ltf_displacement=Displacement(
            direction="BULLISH",
            candle_index=2,
            body_size=0.0018,
            avg_body_ratio=2.8,
            confirmed=True,
        ),
    )
    smc.sweep_detected = SimpleNamespace(reversal_confirmed=True)
    smc.ltf_choch = SimpleNamespace(direction="BULLISH")
    technical = SimpleNamespace(atr_pips=10.0)

    eval_result = scanner._evaluate_setup_v2(
        instrument="EUR_USD",
        profile={},
        smc_analysis=smc,
        technical=technical,
        confidence=90,
        entry_price=1.1000,
        stop_loss=1.0988,
        risk_reward=3.5,
    )

    assert eval_result.gates["fvg_valid"] is True
    assert eval_result.allow_trade is True
    assert eval_result.details["strict_fvg_count"] >= 1

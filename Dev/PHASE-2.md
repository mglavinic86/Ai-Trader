# FAZA 2: Core Trading

> Cilj: Order management, position sizing, risk management, SQLite logging

---

## Prerequisites

- Faza 1 završena ✅
- OANDA credentials u `.env` (može se testirati i bez)

---

## Tasks - ALL COMPLETED ✅

### Task 2.1: Position Sizer ✅
- [x] `src/trading/position_sizer.py`
  - [x] Confidence-based risk tiers (1-3%)
  - [x] Position size calculator
  - [x] Risk amount calculator
  - [x] Risk/reward calculator

### Task 2.2: Risk Manager ✅
- [x] `src/trading/risk_manager.py`
  - [x] Hard-coded limits validation
  - [x] Pre-trade checklist
  - [x] Trade validation
  - [x] Daily drawdown tracking

### Task 2.3: Order Management ✅
- [x] `src/trading/orders.py`
  - [x] `open_position()` - market order with SL/TP
  - [x] `close_position()` - close by instrument
  - [x] `close_all_positions()` - emergency function
  - [x] `modify_position()` - update SL/TP
  - [x] `move_stop_to_breakeven()`
  - [x] `get_open_trades()`

### Task 2.4: Database Setup ✅
- [x] `src/utils/database.py`
  - [x] SQLite connection with context manager
  - [x] Trades table with full schema
  - [x] Decisions table
  - [x] Errors table (RAG memory)
  - [x] CRUD operations
  - [x] Performance statistics

### Task 2.5: Trade Logger ✅
- [x] `db.log_trade()` - log to SQLite
- [x] `db.log_decision()` - log decisions
- [x] `db.log_error()` - log errors for RAG
- [x] `db.find_similar_errors()` - RAG query
- [x] `db.get_daily_pnl()` - daily P/L tracking

### Task 2.6: CLI Scripts ✅
- [x] `scripts/execute_trade.py` - full trade execution with validation
- [x] `scripts/emergency_close.py` - close all positions

---

## Acceptance Criteria

### Faza 2 je DONE kada:

```bash
# Ova komanda radi:
python scripts/execute_trade.py EUR_USD LONG --sl 1.0800 --tp 1.0900

# Output:
# Pre-trade checklist:
# [✓] Confidence 75% ≥ 50%
# [✓] Risk 2% within tier limit
# [✓] Daily drawdown 0.5% < 3%
# [✓] Open positions 0 < 3
# [✓] Spread 1.2 pips < 3
#
# Trade Details:
# ─────────────────────────────
# Instrument: EUR/USD
# Direction:  LONG
# Entry:      1.0843
# Stop Loss:  1.0800
# Take Profit: 1.0900
# Size:       2,500 units
# Risk:       $100 (1%)
#
# Execute trade? (yes/no):
```

---

## Code Specifications

### position_sizer.py
```python
def calculate_position_size(
    equity: float,
    confidence: int,
    entry_price: float,
    stop_loss: float,
    instrument: str
) -> dict:
    """
    Returns:
        {
            "units": int,
            "risk_percent": float,
            "risk_amount": float,
            "risk_tier": str,
            "can_trade": bool,
            "reason": str
        }
    """
```

### risk_manager.py
```python
def validate_trade(
    equity: float,
    risk_amount: float,
    open_positions: list,
    daily_pnl: float,
    spread_pips: float
) -> dict:
    """
    Returns:
        {
            "valid": bool,
            "checks": [
                {"name": "risk_limit", "passed": bool, "message": str},
                {"name": "daily_drawdown", "passed": bool, "message": str},
                ...
            ]
        }
    """
```

---

*Verzija: 1.0 | Kreirano: 2026-01-30*

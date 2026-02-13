# AI Trader

> Automated Forex Trading System with AI-Powered Analysis

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![MetaTrader5](https://img.shields.io/badge/MetaTrader-5-green.svg)
![License](https://img.shields.io/badge/License-Proprietary-orange.svg)

---

## Features

| Feature | Description |
|---------|-------------|
| **AI Analysis** | Multi-factor analysis combining technical indicators, sentiment, and adversarial thinking |
| **MT5 Integration** | Direct connection to MetaTrader 5 for real-time prices and order execution |
| **Web Dashboard** | Modern Streamlit-based UI with 10+ pages |
| **Backtesting** | Walk-forward simulation with comprehensive metrics |
| **Auto-Learning** | System learns from mistakes and generates lessons |
| **Risk Management** | Hard-coded limits prevent excessive losses |
| **Performance Analytics** | Detailed statistics, charts, and insights |

---

## Screenshots

| Dashboard | Analysis | Performance |
|-----------|----------|-------------|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Analysis](docs/screenshots/analysis.png) | ![Performance](docs/screenshots/performance.png) |

> *Screenshots placeholders - add actual images to `docs/screenshots/`*

---

## Requirements

### System
- Windows 10/11 (MT5 requirement)
- Python 3.10 or higher
- 4GB RAM minimum

### Software
- [MetaTrader 5 Terminal](https://www.metatrader5.com/en/download) (must be running)
- OANDA TMS Demo Account (or compatible MT5 broker)

### Python Packages
See `requirements.txt` for full list. Key dependencies:
- `MetaTrader5` - MT5 Python API
- `streamlit` - Web dashboard
- `plotly` - Interactive charts
- `pandas` - Data manipulation
- `anthropic` - Claude AI API

---

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd "AI Trader/Dev"
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
copy .env.example .env
# Edit .env with your credentials
```

Required variables in `.env`:
```ini
# MetaTrader 5
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server

# Anthropic API
ANTHROPIC_API_KEY=your_api_key
```

### 5. Configure MetaTrader 5
1. Open MT5 Terminal
2. Go to **Tools > Options > Expert Advisors**
3. Enable:
   - [x] Allow algorithmic trading
   - [x] Allow DLL imports
4. Login to your account
5. Keep MT5 running while using AI Trader

---

## Quick Start

### CLI Mode (Terminal)
```bash
cd Dev
python trader.py
```

Available commands:
```
help              - Show help
price EUR_USD     - Get current price
account           - Account status
positions         - Open positions
analyze EUR/USD   - AI analysis
trade             - Trade workflow
emergency         - Close all positions
exit              - Exit
```

### Web Dashboard Mode
```bash
cd Dev
streamlit run dashboard.py
```
Opens browser at `http://localhost:8501`

---

## Dashboard Pages

| # | Page | Description |
|---|------|-------------|
| 1 | **Dashboard** | Account overview, suggested actions, notifications |
| 2 | **Chat** | AI conversation interface for analysis |
| 3 | **Analysis** | Technical analysis with charts, Simple/Detailed toggle |
| 4 | **Positions** | Position management with health indicators |
| 5 | **History** | Trade history and statistics |
| 6 | **Settings** | Configuration editor |
| 7 | **Skills** | Edit AI skills, knowledge, and system prompt |
| 8 | **Backtest** | Walk-forward backtesting with metrics |
| 9 | **Learn** | Educational content for beginners |
| 10 | **Performance** | Trading statistics, equity curve, analytics |
| 11 | **Monitoring** | System health, error tracking, alerts |
| 12 | **Database** | SQLite browser, SQL editor, maintenance |

---

## Configuration

### Settings Structure
```
settings/
├── system_prompt.md    # AI personality and behavior
├── config.json         # Trading configuration
├── skills/             # AI trading skills
│   ├── trend_analysis.md
│   ├── risk_assessment.md
│   └── ...
└── knowledge/          # Domain knowledge
    ├── forex_basics.md
    ├── technical_indicators.md
    └── ...
```

### Key Configuration (config.json)
```json
{
  "trading": {
    "allowed_pairs": ["EUR_USD", "GBP_USD", "USD_JPY"],
    "max_positions": 3,
    "default_timeframe": "H1"
  },
  "risk": {
    "max_daily_drawdown": 0.03,
    "max_weekly_drawdown": 0.06,
    "confidence_threshold": 50
  }
}
```

---

## Operations Notes (Current Demo)

- Date: `2026-02-10`
- Purpose: bootstrap first executable trades on demo while keeping core SMC governance active.
- Applied settings:
  - `settings/auto_trading.json` -> `dry_run=false`
  - `settings/auto_trading.json` -> `ai_validation.enabled=true`
  - `settings/auto_trading.json` -> `ai_validation.reject_on_failure=false` (demo advisory mode)
  - `settings/auto_trading.json` -> `smc_v2.risk.min_rr.A+=0.1`
  - `settings/auto_trading.json` -> `smc_v2.risk.min_rr.A=0.2`
  - `settings/auto_trading.json` -> `smc_v2.risk.min_rr.B=0.5`
  - `settings/auto_trading.json` -> `smc_v2.grade_execution.enforce_live_hard_gates=false` (demo)
  - `settings/auto_trading.json` -> `smc_v2.risk.fx_sl_caps.max_pips=25.0` (demo)
- Deliberately unchanged:
  - `smc_v2.enabled=true`
  - `grade_execution.enabled=true`
  - `killzone_gate_live=true`
  - `htf_poi_gate_live=true`
  - `market_order_fallback_enabled=false`
- Rationale:
  - system was structurally valid but repeatedly blocked by RR gate before execution.
  - AI validation was still rejecting most demo signals using strict RR policy, so it remains enabled but non-blocking during bootstrap.
- Rollback guidance:
  - after first 3-5 demo executions, restore `ai_validation.reject_on_failure=true`.
  - after initial 3-5 demo executions, gradually restore stricter RR (`A+=3.0`, `A=2.5`, `B=2.0`) and keep config snapshots for each change.

- Runtime/dashboard sync updates (2026-02-11):
  - scanner now writes `scanner_stats` every scan cycle (scan count + average scan duration are live-backed).
  - `auto_signals` stores post-limit-adjustment `entry_price` and `risk_reward` (matches runtime evaluator values).
  - pending limit fill/expiry now propagates to `auto_signals` and `trades` (`AUTO_SCALPING_LIMIT`) for accurate metrics.

---

## Risk Management

**Hard-coded limits that cannot be overridden:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max Position Risk | 1-3% | Based on confidence tier |
| Max Daily Drawdown | 3% | Trading stops if exceeded (auto-resets at UTC midnight) |
| Max Weekly Drawdown | 6% | Trading stops if exceeded (auto-resets on Monday UTC) |
| Max Concurrent Positions | 3 | Prevents over-exposure |
| Min Confidence | 50% | Below this = no trade |
| Max Spread | 3 pips | High spread = no trade |

### Risk Validation Gate (v1.1)

Every trade MUST pass 6 validation checks before execution:

1. **Confidence** >= 50%
2. **Risk per trade** within tier limit (1-3%)
3. **Daily drawdown** < 3%
4. **Weekly drawdown** < 6%
5. **Open positions** < 3
6. **Spread** < 3 pips

Trades without `confidence` and `risk_amount` parameters are **automatically rejected**.

### Confidence Tiers
| Confidence | Max Risk | Tier |
|------------|----------|------|
| 90-100% | 3% | High |
| 70-89% | 2% | Medium |
| 50-69% | 1% | Low |
| < 50% | 0% | No Trade |

---

## Architecture

```
Dev/
├── trader.py              # CLI entry point
├── dashboard.py           # Web dashboard entry point
│
├── src/
│   ├── trading/           # Order execution, MT5 client
│   ├── market/            # Technical indicators
│   ├── analysis/          # AI analysis modules
│   ├── backtesting/       # Backtest engine
│   ├── core/              # Interface, settings
│   └── utils/             # Config, logging, database
│
├── pages/                 # Streamlit pages (11 pages)
├── components/            # Reusable UI components (9 components)
├── settings/              # AI configuration
└── data/                  # SQLite database, backtest reports
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `mt5_client.py` | MetaTrader 5 API wrapper |
| `indicators.py` | EMA, RSI, MACD, ATR, Support/Resistance |
| `confidence.py` | Final confidence score calculator |
| `adversarial.py` | Bull vs Bear case analysis |
| `trade_lifecycle.py` | Auto-learning from closed trades |
| `error_analyzer.py` | Categorizes trading mistakes |

---

## API Reference

### MT5Client
```python
from src.trading.mt5_client import MT5Client

client = MT5Client()
price = client.get_price("EUR_USD")
candles = client.get_candles("EUR_USD", "H1", 100)
account = client.get_account()
positions = client.get_positions()
```

### Analysis Pipeline
```python
from src.market.indicators import TechnicalAnalyzer
from src.analysis.sentiment import SentimentAnalyzer
from src.analysis.adversarial import AdversarialEngine
from src.analysis.confidence import ConfidenceCalculator

# 1. Technical analysis
tech = TechnicalAnalyzer().analyze(candles, instrument)

# 2. Sentiment analysis
sentiment = SentimentAnalyzer().analyze(candles)

# 3. Adversarial thinking
adversarial = AdversarialEngine().analyze(tech, sentiment)

# 4. Final confidence
confidence = ConfidenceCalculator().calculate(tech, sentiment, adversarial)
```

---

## Testing

### Check MT5 Connection
```bash
python scripts/check_connection.py
```

### Run Backtest
```bash
# Via CLI
python trader.py
> backtest EUR_USD H1 2024-01-01 2024-12-31

# Or use the Backtest page in web dashboard
```

### Unit Tests
```bash
python -m pytest tests/
```

---

## Troubleshooting

### MT5 Connection Failed
1. Ensure MT5 terminal is running
2. Check credentials in `.env`
3. Verify "Allow algorithmic trading" is enabled
4. Try restarting MT5 terminal

### "Symbol not found"
- Use correct symbol format: `EURUSD.pro` (not `EUR_USD`)
- The system auto-converts, but check broker's symbol list

### Dashboard Won't Load
```bash
# Kill any existing Streamlit processes
taskkill /f /im streamlit.exe

# Restart
streamlit run dashboard.py
```

---

## Contributing

This is a proprietary project. For internal development:

1. Create feature branch from `main`
2. Follow existing code style
3. Update documentation
4. Submit PR for review

---

## License

**Proprietary Software**

Copyright (c) 2026 Sirius Grupa d.o.o. All rights reserved.

This software is proprietary and confidential. Unauthorized copying, distribution, or use is strictly prohibited.

---

## Disclaimer

**TRADING RISK WARNING**

Trading foreign exchange (Forex) carries a high level of risk and may not be suitable for all investors. Before deciding to trade, you should carefully consider your investment objectives, level of experience, and risk appetite.

The possibility exists that you could sustain a loss of some or all of your initial investment. Therefore, you should not invest money that you cannot afford to lose.

**This software is provided for educational and informational purposes only. It does not constitute financial advice. Past performance is not indicative of future results.**

The developers and owners of this software are not responsible for any financial losses incurred through its use.

---

## Support

For issues and questions:
- Check `PROGRESS.md` for development status
- Review `CLAUDE_CONTEXT.md` for technical details
- Contact: internal support channels

---

*Last updated: 2026-01-31 | Version 1.1 (Security Fixes)*

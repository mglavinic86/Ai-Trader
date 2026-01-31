# AI Trader - Claude Instructions

> **CLAUDE:** Na pocetku sesije procitaj `Dev/CLAUDE_CONTEXT.md` za kompletan kontekst projekta.

---

## Quick Start

```bash
cd Dev
cat CLAUDE_CONTEXT.md   # Procitaj kontekst
```

## Projekt Status (2026-01-31)

| Faza | Status |
|------|--------|
| Faza 1-3 | DONE |
| Faza 3.5: MT5 Integration | DONE |
| Faza 3.6: Web Dashboard | DONE |
| Faza 4.1: Backtesting | DONE |
| Faza 4.2: Auto Learning | DONE |
| Faza 4.3: UX Improvements | DONE |
| Faza 4.4: Performance Analytics | DONE |
| Faza 4.5: Docs & Monitoring | DONE |
| Faza 4.6: Risk Validation Gate | DONE |
| Faza 4.7: SMC Knowledge Integration | DONE |
| Faza 4.8: Security Fixes | DONE |
| Faza 4.9: Remote Access | DONE |
| Faza 4: Production | IN PROGRESS (100%) |

## VAZNO: MT5 Integracija

**OANDA je zamijenjen s MetaTrader 5!**

- Account: `62859209`
- Server: `OANDA-TMS-Demo`
- Balance: `50,000 EUR`
- Status: **TESTIRANO I RADI**

## Pokretanje

### CLI (Terminal)
```bash
cd Dev
python trader.py
```

### Web Dashboard
```bash
cd Dev
python -m streamlit run dashboard.py --server.address 0.0.0.0
```
Otvara browser na `http://localhost:8501`

### Auto-Start (Windows Startup)
Dashboard se automatski pokrece kad se Windows upali.
- `Dev/start_dashboard.bat` - Batch skripta
- `Dev/start_dashboard_hidden.vbs` - Pokrece bez CMD prozora

### Remote Access (Tailscale)
Pristup s mobitela/tableta preko privatne VPN mreze:
- **PC IP:** `100.106.24.4`
- **Mobile URL:** `http://100.106.24.4:8501`
- Instaliran Tailscale na PC i Samsung S24
- Zero-config, end-to-end encrypted (WireGuard)

## Kljucni fajlovi

| Prioritet | Fajl |
|-----------|------|
| 1 | `Dev/CLAUDE_CONTEXT.md` - Session kontekst |
| 2 | `Dev/PROGRESS.md` - Detaljan napredak |
| 3 | `Dev/dashboard.py` - Web Dashboard entry point |
| 4 | `Dev/src/trading/mt5_client.py` - MT5 API |
| 5 | `Dev/src/trading/trade_lifecycle.py` - Auto learning handler |
| 6 | `Dev/settings/system_prompt.md` - AI ponasanje |

## Web Dashboard Stranice

| # | Stranica | Opis |
|---|----------|------|
| 1 | Dashboard | Account overview + Suggested Actions |
| 2 | Chat | AI analiza (glavna) |
| 3 | Analysis | Technical analysis + Simple/Detailed toggle |
| 4 | Positions | Position management + Health indicators |
| 5 | History | Trade history |
| 6 | Settings | Konfiguracija |
| 7 | Skills | **EDITOR** za Skills/Knowledge/System Prompt |
| 8 | Backtest | Walk-forward backtesting s metrikama |
| 9 | Learn | **NOVO** - Edukacija za pocetnike |
| 10 | Performance | Trading statistike i grafovi |
| 11 | Monitoring | System health, errors, alerts |
| 12 | Database | **NOVO** - SQLite browser, SQL editor |

## UX Features (Session 6-8)

- Welcome Wizard za onboarding
- Tooltips na svim metrikama
- Suggested Actions kartice
- Position Health indikatori
- Notification system
- Help & Resources button
- Simple/Detailed toggle
- Status bar na svim stranicama

## NOVO: Risk Validation Gate (Session 9)

**`OrderManager.open_position()` sada ZAHTIJEVA risk validaciju!**

```python
# STARO - moglo zaobici provjere
om.open_position("EUR_USD", 1000, stop_loss=1.08)

# NOVO - MORA imati confidence i risk_amount
om.open_position("EUR_USD", 1000, stop_loss=1.08,
                 confidence=75, risk_amount=500)
```

## NOVO: SMC Knowledge Integration (Session 10)

**56 PDF-ova iz "novi skillovi" foldera integrirano u sustav!**

### Novi Knowledge Fajlovi
```
settings/knowledge/
├── market_structure.md    # HTF/LTF alignment, candle-to-structure
├── fair_value_gap.md      # FVG, iFVG, entry rules
├── order_blocks.md        # OB identification, entry methods
├── liquidity.md           # BSL/SSL, PDH/PDL, PWH/PWL
├── bos_cisd.md            # Break of Structure vs CISD
├── entry_models.md        # 3 ICT entry modela
└── session_trading.md     # Killzone strategies
```

### Novi Skill Fajlovi
```
settings/skills/
├── smc_trading.md         # Smart Money Concepts full workflow
├── fvg_strategy.md        # FVG-based trading
└── killzone_trading.md    # London/NY session strategies
```

### System Prompt
- Azuriran s SMC workflow (11 koraka)
- Primjer analize s FVG/OB/CISD
- Session i Liquidity preferences

## NOVO: Security Fixes (Session 11)

**6 kriticnih sigurnosnih bugova popravljeno!**

| Fix | Opis |
|-----|------|
| Weekly drawdown | Sada se PROVJERAVA (6% limit) |
| Auto-reset | Daily/weekly P/L reset na UTC granicama |
| Global bypass | UKLONJEN - samo per-call bypass |
| Equity fallback | Trade se odbija ako equity nedostupan |
| Pip calculation | Koristi MT5 symbol_info za sve instrumente |
| Volume rounding | Koristi broker volume_step |

**Test coverage:** 32 testa (14 + 13 + 5)

## NOVO: Remote Access (Session 12)

**Pristup dashboardu s mobitela bilo gdje!**

| Komponenta | Detalj |
|------------|--------|
| VPN | Tailscale (WireGuard) |
| PC IP | `100.106.24.4` |
| Mobile | Samsung S24 (`100.74.221.115`) |
| URL | `http://100.106.24.4:8501` |
| Auto-start | Windows Startup skripta |

### Fajlovi
```
Dev/
├── start_dashboard.bat          # Batch skripta
└── start_dashboard_hidden.vbs   # Hidden launcher (Startup)
```

## Sljedece (Faza 4)

- ~~Backtesting modul~~ DONE
- ~~Auto Learning~~ DONE
- ~~Performance analytics~~ DONE
- ~~UX Improvements~~ DONE
- ~~Documentation~~ DONE (README.md)
- ~~Error monitoring~~ DONE
- ~~Risk Validation Gate~~ DONE
- ~~SMC Knowledge Integration~~ DONE
- ~~Security Fixes~~ DONE
- Live demo testing

---

*Zadnje azuriranje: 2026-01-31 | Session 12 - Remote Access DONE*

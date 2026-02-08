# FTMO Integration Plan

> **Status:** PLANIRANO - za naknadnu implementaciju
> **Datum:** 2026-02-07

---

## Sto je FTMO?

Prop trading firma - daje traderima pristup velikom kapitalu (25k-200k) nakon sto prodju evaluaciju. Profit split 80-90% u korist tradera.

## FTMO Challenge pravila

| Pravilo | Challenge | Verification | Funded |
|---------|-----------|--------------|--------|
| Profit Target | 10% | 5% | Nema |
| Max Daily Loss | 5% | 5% | 5% |
| Max Total Loss | 10% | 10% | 10% |
| Min Trading Days | 4 | 4 | - |
| Time Limit | 30 dana | 60 dana | Nema |

## Kompatibilnost s AI Trader

**FTMO nudi MT5 platformu** - nas sustav vec koristi MT5 preko `mt5_client.py`.

Promjena je minimalna:
```
Trenutno:  MT5 -> OANDA-TMS-Demo (account 62859209)
FTMO:      MT5 -> FTMO-Server (account XXXXXX)
```

**VAZNO:** Kod odabira FTMO accounta izabrati **MetaTrader 5** varijantu (ne MT4, cTrader ili DXtrade).

## Potrebne prilagodbe

### 1. FTMO Risk Management modul (NOVI)

Lokacija: `Dev/src/trading/ftmo_risk_manager.py`

Funkcionalnosti:
- **Daily drawdown monitor** - hard stop na 4.5% (safety margin ispod 5% FTMO limita)
- **Total drawdown monitor** - hard stop na 9% (safety margin ispod 10% FTMO limita)
- **Profit target tracker** - prati napredak prema 10% cilju
- **Phase detection** - zna je li Challenge, Verification ili Funded
- **Emergency shutdown** - automatski zatvara sve pozicije ako se priblizi limitu

### 2. Adaptive agresivnost

- Konzervativniji kad si blizu drawdown limita
- Agresivniji kad imas profit buffer
- Primjer: na 8% total drawdown, smanjiti risk na 0.1% po tradeu ili potpuno stati

### 3. Profit target strategija

- Prvih 20 dana: normalno tradanje (risk 0.3%)
- Kad si na 7-8% profita: smanjiti risk, zastititi profit
- Kad si na 9%+: minimalan risk, jedan dobar trade za zatvoriti challenge

### 4. Config promjene

```json
{
  "ftmo": {
    "enabled": false,
    "phase": "challenge",
    "account_size": 100000,
    "max_daily_drawdown_pct": 4.5,
    "max_total_drawdown_pct": 9.0,
    "profit_target_pct": 10.0,
    "safety_margin_pct": 0.5,
    "reduce_risk_at_drawdown_pct": 3.0,
    "stop_trading_at_drawdown_pct": 4.0
  }
}
```

### 5. Dashboard stranica

Nova stranica ili tab na AutoTrading:
- FTMO progress bar (profit target)
- Daily drawdown gauge (zeleno/zuto/crveno)
- Total drawdown gauge
- Preostali dani
- Min trading days status

## Preduvjeti prije FTMO pokusaja

1. [ ] Sustav mora biti profitabilan na demo accountu (min 2 tjedna)
2. [ ] Win rate > 40%
3. [ ] ISI calibrator kalibriran (min 30 tradeova)
4. [ ] Dry run = false, provjereno da izvrsava tradeove korektno
5. [ ] FTMO Risk Management modul implementiran i testiran
6. [ ] Backtest na historical data s FTMO pravilima

## Procjena troskova

| Account Size | FTMO Fee | Refundable? |
|-------------|----------|-------------|
| 10,000 EUR | ~155 EUR | Da, nakon prvog profit splita |
| 25,000 EUR | ~250 EUR | Da |
| 50,000 EUR | ~345 EUR | Da |
| 100,000 EUR | ~540 EUR | Da |
| 200,000 EUR | ~1,080 EUR | Da |

Fee se vraca nakon prvog uspjesnog profit splita na funded accountu.

## Rizici

- **Trailing drawdown** - neke FTMO varijante imaju trailing max loss (pomice se s profitom)
- **Overnight/Weekend positions** - FTMO moze imati ogranicenja
- **News trading** - neki prop firmovi ogranicavaju tradanje oko high-impact vijesti
- **Consistency rule** - jedan dan ne smije ciniti vise od 45% ukupnog profita (novije pravilo)

## Alternativne prop firme

Ako FTMO ne odgovara, razmotriti:
- **The Funded Trader**
- **MyFundedFX**
- **True Forex Funds**
- **E8 Funding**

Sve koriste MT5 - ista kompatibilnost s nasim sustavom.

---

*Zapisano: 2026-02-07 | Za implementaciju kad sustav bude profitabilan na demo*

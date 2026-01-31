# Značajke (Features) - AI TRADER (Claude Code)

## Core Features (MVP)

### Faza 1: Foundation
- [ ] OANDA demo account + API setup
- [ ] Python environment (venv)
- [ ] Price fetching via OANDA API
- [ ] Basic project structure
- [ ] Environment configuration (.env)
- [ ] **Basic logging setup**

### Faza 2: Core Trading
- [ ] Order management (market orders)
- [ ] Position sizing calculator (confidence-based tiers)
- [ ] Risk management hard limits
- [ ] Basic technical indicators
- [ ] Trade logging (SQLite)
- [ ] **Comprehensive logging system**

### Faza 3: AI Integration
- [ ] Claude market analysis
- [ ] **Adversarial thinking (Bull vs Bear)**
- [ ] Trade suggestions with confidence scores
- [ ] Human approval workflow
- [ ] Analysis templates
- [ ] **Sentiment analysis integration**

### Faza 4: Learning & Production
- [ ] **RAG za greške (error memory)**
- [ ] Performance tracking
- [ ] Trade journaling
- [ ] Backtesting module
- [ ] Historical data analysis

---

## Nove Značajke (v2.0)

### Adversarial Thinking
Prije svakog tradea, sustav prolazi kroz strukturiranu Bull vs Bear debatu:

```
BULL CASE:
- Tehnički razlozi za trade
- Fundamentalni faktori
- Sentiment podrška

BEAR CASE:
- Kontra-indikatori
- Rizici i opasnosti
- Što može poći po zlu

VERDICT:
- Score balance
- Final recommendation
```

### Sentiment Analysis
Analiza tržišnog sentimenta iz dostupnih izvora:

| Izvor | Metoda | Output |
|-------|--------|--------|
| Price action | Tehnički indikatori | -1 to +1 |
| News headlines | Keyword analysis | Bullish/Bearish/Neutral |
| Economic calendar | Event impact | Risk score |

**Combined sentiment score:** -1.0 (extremely bearish) to +1.0 (extremely bullish)

### RAG Error Memory
Sustav pamti sve gubitničke tradeove i uči iz njih:

- **Kategorije grešaka:** NEWS_IGNORED, OVERCONFIDENT, COUNTER_TREND, POOR_TIMING, CORRELATION, REVENGE_TRADE
- **Query prije tradea:** "Jesam li radio ovu grešku prije?"
- **Weekly review:** Top 3 ponovljene greške
- **Auto-penalizacija:** Sličan setup = smanjen confidence

### Comprehensive Logging
Tri razine logiranja:

1. **Trade Log** - svaki izvršeni trade s punim detaljima
2. **Decision Log** - svaka analiza, čak i ako nije rezultirala tradeom
3. **Error Log** - svi gubici s root cause analizom

---

## Risk Tiers (NOVO)

| Confidence | Risk % | Uvjet |
|------------|--------|-------|
| 90-100% | 3% | Svi faktori poravnati |
| 70-89% | 2% | Većina faktora OK |
| 50-69% | 1% | Minimalni rizik |
| < 50% | 0% | NE TRADATI |

---

## Feature Backlog

| ID | Značajka | Prioritet | Faza | Status |
|----|----------|-----------|------|--------|
| F01 | OANDA API wrapper | HIGH | 1 | Pending |
| F02 | Price fetching | HIGH | 1 | Pending |
| F03 | Order execution | HIGH | 2 | Pending |
| F04 | Position sizing (tiers) | HIGH | 2 | Pending |
| F05 | Risk limits | CRITICAL | 2 | Pending |
| F06 | **Logging system** | HIGH | 2 | Pending |
| F07 | Claude analysis | HIGH | 3 | Pending |
| F08 | **Adversarial thinking** | HIGH | 3 | **NEW** |
| F09 | **Sentiment analysis** | MEDIUM | 3 | **NEW** |
| F10 | Human approval | HIGH | 3 | Pending |
| F11 | **RAG error memory** | HIGH | 4 | **NEW** |
| F12 | Trade journal | MEDIUM | 4 | Pending |
| F13 | Backtesting | MEDIUM | 4 | Pending |

---

## CLI Workflow Examples (Updated)

### Full Analysis with Adversarial
```
Ti: "Analiziraj EUR/USD"

Claude: Analyzing EUR/USD...

📊 TECHNICAL ANALYSIS
- Trend: Bullish (D1 EMA20 > EMA50)
- RSI(14): 58 (neutral)
- Support: 1.0800 | Resistance: 1.0880

📰 SENTIMENT ANALYSIS
- News sentiment: +0.3 (mildly bullish)
- Economic calendar: ECB tomorrow (HIGH IMPACT)
- Combined score: +0.2

⚔️ ADVERSARIAL ANALYSIS

BULL CASE:
✓ D1 trend clearly bullish
✓ Support at 1.0800 holding strong
✓ RSI not overbought, room to run

BEAR CASE:
✗ ECB meeting tomorrow - high volatility expected
✗ Resistance at 1.0880 is close (37 pips)
✗ USD showing strength last 3 days

⚠️ RAG CHECK: Similar pre-ECB setup lost 2% on 2026-01-15

📋 VERDICT
Confidence: 62% (BEAR case has valid points)
Recommended risk: 1% (tier 1)
Suggestion: WAIT until after ECB, or trade with minimal size

Želiš li tradati? (da/ne/wait)
```

### Trade Execution with Logging
```
Ti: "Da, 1% risk"

Claude: Executing trade...

✅ PRE-TRADE CHECKLIST
[✓] Confidence 62% ≥ 50%
[✓] Risk 1% within tier
[✓] Daily DD: 0.5% < 3%
[✓] Positions: 0/3
[✓] Spread: 1.1 pips < 3
[✓] Adversarial: COMPLETED
[✓] RAG check: WARNING noted
[✓] Sentiment: +0.2

📝 TRADE LOGGED
ID: 2026-01-30-001
Pair: EUR_USD LONG
Entry: 1.0843
SL: 1.0800 (43 pips)
TP: 1.0900 (57 pips)
Size: 2,326 units
Risk: $100 (1%)

Trade executed successfully.
```

### Post-Loss Analysis
```
[Trade closed at SL]

Claude: Trade 2026-01-30-001 closed at loss.

📉 LOSS ANALYSIS
P/L: -$100 (-1%)
Duration: 4h 23m
Exit reason: Stop loss hit

🔍 ROOT CAUSE ANALYSIS
Category: NEWS_IGNORED
- ECB caused 80 pip spike against position
- BEAR case warning was correct
- Should have waited for event

📚 ADDED TO RAG:
"Pre-ECB long EUR/USD with resistance nearby - HIGH RISK"

Lesson: Don't trade EUR pairs 24h before ECB.
```

---

## Što je izbačeno iz originalnog plana

| Značajka | Razlog izbacivanja |
|----------|-------------------|
| Telegram bot | CLI je sučelje |
| Discord bot | CLI je sučelje |
| VPS deployment | Lokalno računalo |
| Docker | Python venv |
| Multi-channel | Samo CLI |

## Što je dodano (v2.0)

| Značajka | Razlog dodavanja |
|----------|-----------------|
| Adversarial thinking | Industrijsko best practice (LLM-TradeBot) |
| RAG error memory | Učenje iz grešaka (Day 85 lessons) |
| Sentiment analysis | Dodatni faktor za odluke |
| Confidence-based risk | Dinamičniji risk management |
| Comprehensive logging | Debugging + post-mortem |

---
*Ažurirano: 2026-01-30 | v2.0 - Adversarial, RAG, Sentiment, Logging*

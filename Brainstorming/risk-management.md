# Risk Management - AI TRADER

> **KRITIČNO:** Core parametri su hard-coded i NE MOGU biti overrideani od strane AI-a.

---

## Hard Limits

| Parametar | Vrijednost | Napomena |
|-----------|------------|----------|
| Max risk per trade | **1-3% equity** | Ovisno o confidence score |
| Max daily drawdown | **3% equity** | Auto-stop trading |
| Max weekly drawdown | **6% equity** | Human review |
| Max concurrent positions | **3** | Diversifikacija |
| Max correlation exposure | **2 pairs** | USD exposure |

### Risk Tiers (novo)

| Confidence Score | Max Risk | Kada koristiti |
|------------------|----------|----------------|
| 90-100% | 3% | Iznimno jak setup, svi faktori poravnati |
| 70-89% | 2% | Dobar setup, većina faktora poravnata |
| 50-69% | 1% | Solidan setup, minimalni rizik |
| < 50% | 0% | **NE TRADATI** |

---

## Adversarial Thinking (NOVO)

Prije svakog tradea, Claude mora proći kroz **Bull vs Bear analizu**:

### Workflow:
```
1. BULL CASE: Zašto bi ovaj trade uspio?
   - Tehnički razlozi
   - Fundamental razlozi
   - Sentiment razlozi

2. BEAR CASE: Zašto bi ovaj trade propao?
   - Kontra-indikatori
   - Rizici
   - Što može poći po zlu?

3. VERDICT:
   - Ako BEAR case ima jake argumente → SKIP
   - Ako BULL prevladava → Proceed s odgovarajućim rizikom
```

### Primjer:
```
BULL CASE (EUR/USD Long):
- D1 trend bullish (EMA20 > EMA50)
- RSI nije overbought (58)
- Support na 1.0800 drži

BEAR CASE (EUR/USD Long):
- ECB sutra - volatilnost
- USD strength zadnjih dana
- Resistance na 1.0880 blizu

VERDICT: BEAR ima validan point (ECB).
→ Ili SKIP ili smanjiti risk na 1%
```

---

## RAG za Greške (NOVO)

Sustav pamti sve loše tradeove za buduće učenje.

### Struktura error loga:
```json
{
  "trade_id": "2026-01-30-001",
  "pair": "EUR_USD",
  "direction": "LONG",
  "entry": 1.0843,
  "exit": 1.0790,
  "pnl": -53,
  "pnl_percent": -0.5,
  "error_category": "NEWS_IGNORED",
  "lessons": [
    "ECB meeting was scheduled - should have reduced size",
    "Ignored BEAR case warning about event risk"
  ],
  "tags": ["news_event", "ignored_warning", "oversized"]
}
```

### Error Categories:
| Kategorija | Opis |
|------------|------|
| `NEWS_IGNORED` | Ignoriran high-impact event |
| `OVERCONFIDENT` | Prevelik risk za setup kvalitetu |
| `COUNTER_TREND` | Trade protiv većeg trenda |
| `POOR_TIMING` | Loš entry/exit timing |
| `CORRELATION` | Previše koreliranih pozicija |
| `REVENGE_TRADE` | Trade nakon gubitka (emotivno) |

### Kako se koristi:
1. Prije svakog novog tradea, query RAG: "Jesam li napravio sličnu grešku prije?"
2. Ako da → prikaži upozorenje + smanji confidence score
3. Weekly review: top 3 ponovljene greške

---

## Logging (NOVO)

### Trade Log (svaki trade):
```
timestamp: 2026-01-30T14:23:00Z
pair: EUR_USD
direction: LONG
entry_price: 1.0843
stop_loss: 1.0800
take_profit: 1.0920
position_size: 3000 units
risk_amount: $43
risk_percent: 0.86%
confidence_score: 75
bull_case_summary: "D1 bullish, support holding"
bear_case_summary: "ECB tomorrow, resistance near"
sentiment_score: 0.6 (bullish)
decision: APPROVED
execution_time: 230ms
slippage: 0.2 pips
```

### Decision Log (svaka analiza):
```
timestamp: 2026-01-30T14:20:00Z
pair: EUR_USD
analysis_type: FULL
technical_score: 72
fundamental_score: 65
sentiment_score: 60
combined_score: 66
recommendation: LONG with 1% risk
adversarial_passed: true
rag_warnings: ["Similar setup lost on 2026-01-15"]
final_decision: PROCEED with caution
```

### Error Log:
```
timestamp: 2026-01-30T15:00:00Z
type: TRADE_LOSS
trade_id: 2026-01-30-001
loss_amount: $53
root_cause: NEWS_IGNORED
action_taken: Added to RAG corpus
prevention: "Check economic calendar before ALL trades"
```

---

## Position Sizing Formula

```python
def calculate_position_size(
    equity: float,
    confidence_score: int,  # 0-100
    entry_price: float,
    stop_loss: float
) -> tuple[int, float]:
    """
    Returns (units, risk_percent)
    """
    # Determine risk tier based on confidence
    if confidence_score >= 90:
        risk_percent = 3.0
    elif confidence_score >= 70:
        risk_percent = 2.0
    elif confidence_score >= 50:
        risk_percent = 1.0
    else:
        return 0, 0.0  # DO NOT TRADE

    risk_amount = equity * (risk_percent / 100)
    pip_distance = abs(entry_price - stop_loss) / 0.0001
    pip_value_per_unit = 0.0001

    units = int(risk_amount / (pip_distance * pip_value_per_unit))
    return units, risk_percent

# Primjer: $10,000 equity, 75% confidence, 43 pip SL
# Risk tier = 2%, Risk = $200
# Units = $200 / (43 * 0.0001) ≈ 4,651 units
```

---

## Event-Based Risk Rules

| Event | Akcija |
|-------|--------|
| NFP / FOMC | Flatten all positions 30 min prije |
| High impact news | Max 1% risk (ignore confidence tier) |
| Friday 20:00 UTC | Close sve pozicije (weekend risk) |
| Spread > 3 pips | No new entries |
| After 3% daily loss | **AUTO-STOP** do sutra |

---

## Pre-Trade Checklist

AI mora provjeriti SVE prije tradea:

- [ ] Confidence score ≥ 50%
- [ ] Risk within tier limit (1-3%)
- [ ] Daily drawdown < 3%
- [ ] Weekly drawdown < 6%
- [ ] Open positions < 3
- [ ] No high-impact news in next 30min
- [ ] Spread < 3 pips
- [ ] Not Friday after 20:00 UTC
- [ ] Correlation check passed
- [ ] **Adversarial analysis completed**
- [ ] **RAG check for similar past errors**
- [ ] **Sentiment score calculated**

---

## Drawdown Recovery

| Drawdown | Akcija |
|----------|--------|
| 3% daily | Auto-stop trading do sutra |
| 6% weekly | Human review obavezan |
| 10% monthly | Full stop, strategija audit |

---
*Ažurirano: 2026-01-30 | Dodano: Adversarial, RAG, Logging, Risk Tiers*

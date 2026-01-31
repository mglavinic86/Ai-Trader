# Timeline - AI TRADER (Claude Code)

## Implementacijski plan (6-8 tjedana)

---

### FAZA 1: Foundation (Tjedan 1-2)
- [ ] OANDA demo account + API setup
- [ ] Python environment (venv, requirements.txt)
- [ ] OANDA API wrapper (price fetching)
- [ ] Basic project structure
- [ ] .env configuration

**Milestone:** `python fetch_prices.py EUR_USD` vraća cijenu

---

### FAZA 2: Core Trading (Tjedan 3-4)
- [ ] Order management (open/close positions)
- [ ] Position sizing calculator
- [ ] Risk management hard limits
- [ ] Basic technical indicators (pandas-ta)
- [ ] Trade logging (SQLite)

**Milestone:** Možeš izvršiti trade iz CLI-a

---

### FAZA 3: AI Integration (Tjedan 5-6)
- [ ] Claude analysis prompts
- [ ] Market analysis workflow
- [ ] Economic calendar integration
- [ ] Trade suggestion system
- [ ] Human approval flow (CLI confirmation)

**Milestone:** Claude predlaže trade, ti odobravaš

---

### FAZA 4: Production (Tjedan 7-8)
- [ ] Performance tracking
- [ ] Trade journaling
- [ ] Backtesting na historical data
- [ ] Live testing na demo account
- [ ] Dokumentacija

**Milestone:** Sustav spreman za live trading

---

## Milestone Summary

| Tjedan | Milestone | Deliverable |
|--------|-----------|-------------|
| 2 | Price Data | Fetch cijena iz OANDA |
| 4 | Manual Trading | Execute orders via Python |
| 6 | AI Suggestions | Claude predlaže, ti odobravaš |
| 8 | Production Ready | Demo testiran, spreman za live |

---

## Usporedba s originalnim planom

| Aspekt | Moltbot (staro) | Claude Code (novo) |
|--------|-----------------|-------------------|
| Trajanje | 12 tjedana | 6-8 tjedana |
| DevOps setup | 2 tjedna | 0 (lokalno) |
| Telegram/Discord | 1 tjedan | 0 (CLI) |
| Docker/VPS | 1 tjedan | 0 |
| Kompleksnost | Visoka | Niska |

**Ušteda: ~4 tjedna** jer nema infrastrukture za postavljati.

---

## Sljedeći koraci (ODMAH)

1. **Otvori OANDA Practice Account (demo)**
   - https://www.oanda.com/eu-en/trading/demo-account/

2. **Setup Python environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install httpx pandas python-dotenv
   ```

3. **Dohvati OANDA API credentials**
   - Account ID
   - API Token (Practice)

4. **Napravi prvi price fetch**
   ```python
   # Testni poziv
   python scripts/fetch_prices.py EUR_USD
   ```

---

## Daily Workflow (nakon implementacije)

```
Jutro (prije tržišta):
1. Otvori Claude Code
2. "Analiziraj EUR/USD za danas"
3. Claude daje analizu + preporuku
4. Ako ima dobar setup → odobri trade

Tijekom dana:
1. "Kakav je status pozicija?"
2. "Ažuriraj stop loss na break-even"

Večer:
1. "Daj mi pregled dana"
2. "Zapiši trade journal"
```

---

> Testiraj minimalno 3 mjeseca na demo accountu prije live tradinga!

---
*Ažurirano: 2026-01-30 | Claude Code lokalna arhitektura*

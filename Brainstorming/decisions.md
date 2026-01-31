# Odluke - AI TRADER

## Format zapisa
```
### [DATUM] Naslov odluke
**Kontekst:** Zašto je odluka bila potrebna
**Opcije:** Koje opcije smo razmatrali
**Odluka:** Što smo odlučili
**Razlog:** Zašto smo to odlučili
```

---

## Popis odluka

### [2026-01-30] PIVOT: Moltbot → Claude Code lokalni sustav
**Kontekst:** Originalni plan je bio koristiti Moltbot kao gateway s Telegram/Discord sučeljem na VPS-u. Prevelika kompleksnost za interni sustav.

**Opcije:**
1. Moltbot na VPS-u (Telegram, Docker, Terraform...)
2. Claude Code lokalno (Python skripte, CLI)

**Odluka:** Claude Code lokalni sustav

**Razlog:**
- **Jednostavnije** - nema DevOps-a (VPS, Docker, Terraform)
- **Jeftinije** - ~50% ušteda mjesečno (nema VPS, Pinecone)
- **Brži development** - 6-8 tjedana umjesto 12
- **Natural fit** - Claude Code već koristiš, nema novog alata
- **Human-in-the-loop** - direktno u terminalu, bez Telegram buttona
- **MCP serveri** - memory, filesystem već konfigurirani

**Što je izbačeno:**
- VPS hosting
- Docker Compose
- Terraform/Ansible
- Telegram/Discord bot
- PostgreSQL + TimescaleDB
- Redis
- Pinecone/Chroma
- Node.js/TypeScript

---

### [2026-01] Odabir brokera
**Kontekst:** Potreban forex broker s dobrim API-em za automatizaciju
**Opcije:**
1. OANDA - REST + Streaming, odlična dokumentacija
2. Interactive Brokers - Profesionalni, niži spreadovi
3. MetaTrader 5 - Popularno, Python library

**Odluka:** OANDA za početak
**Razlog:**
- Najbolja dokumentacija
- $0 minimum deposit
- Demo account za testiranje
- FCA/CFTC regulacija
- Može se kasnije migrirati na IB za scaling

---

### [2026-01] Odabir AI modela
**Kontekst:** Potreban LLM za analizu i odluke
**Opcije:**
1. Claude Opus 4.5 - Najbolji reasoning
2. GPT-4o - Popularan, brz
3. Lokalni model - Privatnost

**Odluka:** Claude Opus 4.5 via Claude Code
**Razlog:**
- Najviše otporan na prompt injection
- Najbolji reasoning za kompleksne analize
- Direktna integracija s Claude Code
- Može koristiti Sonnet za jednostavnije analize (cost optimization)

---

### [2026-01] Risk Management Parametri
**Kontekst:** Definiranje hard-coded limita koji ne mogu biti overrideani
**Odluka:**
| Parametar | Vrijednost |
|-----------|------------|
| Max risk per trade | 1% equity |
| Max daily drawdown | 3% equity |
| Max weekly drawdown | 6% equity |
| Max concurrent positions | 3 |
| Max leverage | 10:1 |

**Razlog:** Konzervativni pristup za zaštitu kapitala

---

### [2026-01] Timeframe fokus
**Kontekst:** Claude ne može reagirati u milisekundama
**Odluka:** Fokus na H1, H4, D1 chartove
**Razlog:** AI je bolji za analizu na višim timeframeovima, ne za scalping

---

### [2026-01] Event-based risk rules
**Kontekst:** High-impact news može uzrokovati slippage i volatilnost
**Odluka:**
- NFP/FOMC: Flatten all positions 30 min prije
- High impact news: Max 0.5% risk
- Friday 20:00 UTC: Close sve pozicije (weekend risk)
- Spread > 3 pips: No new entries

**Razlog:** Zaštita od gap-ova i ekstremne volatilnosti

---

### [2026-01-30] Tech Stack (ažurirano)
**Kontekst:** Pojednostavljeni stack za lokalni sustav
**Odluka:**
| Komponenta | Tehnologija |
|------------|-------------|
| Runtime | Python 3.11+ |
| HTTP | httpx |
| Data | pandas |
| TA | pandas-ta |
| DB | SQLite |
| Config | python-dotenv |
| AI | Claude Code (Opus 4.5) |

**Razlog:** Minimalni stack, bez eksterne infrastrukture

---

### [2026-01-30] Dodavanje Adversarial Thinking
**Kontekst:** Istraživanje industrijskog best practice (LLM-TradeBot, TradingAgents)
**Odluka:** Implementirati Bull vs Bear self-debate prije svakog tradea
**Razlog:**
- Smanjuje overconfidence
- Identificira rizike koji bi inače bili ignorirani
- Industrija koristi multi-agent adversarial sustave

---

### [2026-01-30] Dodavanje RAG Error Memory
**Kontekst:** Day 85 lessons - sustavi trebaju učiti iz grešaka
**Odluka:** Pamtiti sve gubitničke tradeove i query-ati prije novih
**Razlog:**
- Sprječava ponavljanje istih grešaka
- Automatski penalizira slične setupove
- Weekly review za pattern detection

---

### [2026-01-30] Dodavanje Sentiment Analysis
**Kontekst:** Dodatni faktor za bolje odluke
**Odluka:** Integrirati sentiment score (-1 do +1) u analizu
**Razlog:**
- Price action sentiment
- News sentiment (ako dostupno)
- Economic calendar awareness

---

### [2026-01-30] Promjena Risk Tiers (1% → 1-3%)
**Kontekst:** Fiksni 1% je prekonzervativan za jake setupove
**Odluka:** Dinamički risk based on confidence:
| Confidence | Risk |
|------------|------|
| 90-100% | 3% |
| 70-89% | 2% |
| 50-69% | 1% |
| <50% | 0% (no trade) |

**Razlog:** Maksimizira profit na jakim setupovima, minimizira na slabima

---

### [2026-01-30] Comprehensive Logging
**Kontekst:** Debugging i post-mortem analiza su kritični
**Odluka:** Tri razine logiranja:
1. Trade Log - svaki trade
2. Decision Log - svaka analiza
3. Error Log - svi gubici s root cause

**Razlog:**
- Omogućava debugging
- Post-mortem analiza
- Audit trail

---
*Ažurirano: 2026-01-30 | v2.0 decisions*

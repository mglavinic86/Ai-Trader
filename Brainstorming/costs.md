# Procjena Troškova - AI TRADER (Claude Code)

---

## Mjesečni troškovi

| Stavka | EUR/mjesec | Napomena |
|--------|------------|----------|
| Claude API (via Claude Code) | ~50-100 | Ovisi o volumenu analiza |
| News API (optional) | 0-30 | Free tier dostupan |
| **UKUPNO** | **~50-130** | |

### Što smo eliminirali:
- ~~VPS (Hetzner)~~ - ~15 EUR/mj - **LOKALNO**
- ~~Pinecone~~ - ~20 EUR/mj - **MCP memory server**
- ~~Domain + SSL~~ - ~2 EUR/mj - **NEPOTREBNO**

---

## Jednokratni troškovi

| Stavka | Vrijednost |
|--------|------------|
| Development time | ~60-80 sati (smanjeno!) |
| OANDA demo account | Besplatno |
| OANDA live account | $0 minimum deposit |

---

## Cost Breakdown po fazama

### Faza 1: Foundation
- Claude API: Minimalno (~10-20 EUR za testiranje)
- **Total: ~10-20 EUR/mj**

### Faza 2: Core Trading
- Claude API: ~30 EUR (više analiza)
- **Total: ~30 EUR/mj**

### Faza 3: AI Integration
- Claude API: ~50 EUR (full usage)
- News API: ~20 EUR (ako treba)
- **Total: ~70 EUR/mj**

### Faza 4: Production
- Claude API: ~80-100 EUR
- News feeds: ~30 EUR (optional)
- **Total: ~80-130 EUR/mj**

---

## Usporedba: Stara vs Nova arhitektura

| Stavka | Moltbot (staro) | Claude Code (novo) | Ušteda |
|--------|-----------------|-------------------|--------|
| VPS | ~15 EUR | 0 EUR | 15 EUR |
| Claude API | ~50-100 EUR | ~50-100 EUR | 0 |
| Pinecone/RAG | ~20 EUR | 0 EUR (MCP) | 20 EUR |
| News API | ~50 EUR | ~30 EUR | 20 EUR |
| Domain/SSL | ~2 EUR | 0 EUR | 2 EUR |
| **UKUPNO** | **~137-190 EUR** | **~50-130 EUR** | **~60-90 EUR** |

**Mjesečna ušteda: ~45-50%**

---

## ROI Kalkulacija

Ako sustav ostvaruje samo 2% mjesečno na $10,000:
- Profit: $200/mj (~185 EUR)
- Troškovi: ~100 EUR/mj
- **Net profit: ~85 EUR/mj**

Pri 5% mjesečno:
- Profit: $500/mj (~460 EUR)
- Troškovi: ~100 EUR/mj
- **Net profit: ~360 EUR/mj**

> Trading nosi rizike. Ove projekcije su samo ilustrativne.

---

## Cost Optimization Tips

1. **Claude Sonnet** za rutinske analize (jeftiniji od Opus)
2. **Claude Opus** samo za kompleksne odluke
3. **Free tier** za news API-je na početku
4. **Lokalni cache** za smanjenje API poziva
5. **MCP memory** umjesto plaćenih vector DB-ova

---
*Ažurirano: 2026-01-30 | Claude Code lokalna arhitektura*

# Brainstorming - AI TRADER (Claude Code) v2.1

Automatizirani forex trading sustav s Claude Code CLI sučeljem.

## Nove značajke v2.1
- **Adversarial Thinking** - Bull vs Bear self-debate
- **RAG Error Memory** - učenje iz grešaka
- **Sentiment Analysis** - tržišni sentiment
- **Risk Tiers** - dinamički 1-3% based on confidence
- **Comprehensive Logging** - trade, decision, error logs

## Struktura

| Fajl | Svrha |
|------|-------|
| `ideja.md` | **GLAVNI** detaljan tehnički plan |
| `idea.md` | Sažetak vizije i ciljeva |
| `decisions.md` | Kronološki zapis svih odluka |
| `features.md` | Lista značajki i prioriteti po fazama |
| `architecture.md` | Tehnička arhitektura i tech stack |
| `notes.md` | Bilješke sa brainstorming sesija |
| `risk-management.md` | Hard-coded risk limiti |
| `timeline.md` | Implementacijski plan |
| `security.md` | Sigurnosne mjere i procedure |
| `costs.md` | Procjena troškova |

## Quick Links

- **Broker:** OANDA (demo za početak)
- **AI:** Claude Code (Opus 4.5)
- **Platforma:** Lokalno računalo (Windows)
- **Timeline:** 6-8 tjedana, 4 faze
- **Mjesečni trošak:** ~50-100 EUR (samo Claude API)

## Workflow

1. **Ideje** → `notes.md`
2. **Odluke** → `decisions.md`
3. **Značajke** → `features.md`
4. **Arhitektura** → `architecture.md`
5. **Development** → `../src/` folder

## Status

- [x] Struktura kreirana
- [x] Definirana vizija
- [x] Core features definirani
- [x] Arhitektura odlučena (Claude Code lokalno)
- [x] Risk management definiran
- [x] Timeline postavljen
- [ ] Spremno za development

## Sljedeći koraci

1. Otvori OANDA demo account
2. Setup Python environment lokalno
3. Napravi OANDA API wrapper
4. Počni s Fazom 1 (Foundation)

---
*Projekt: Sirius Grupa d.o.o. | Započet: 2026-01-30*

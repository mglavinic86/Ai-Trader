# Skills - AI Trader

> Skills su dodatne sposobnosti koje možeš dodati AI-u.
> Svaki skill je Markdown fajl s instrukcijama.

## Kako dodati skill

1. Kreiraj `.md` fajl u ovom folderu
2. Napiši instrukcije za AI
3. Dodaj skill ime u `config.json` -> `skills.custom`

## Primjer skill fajla

```markdown
# Skill: Scalping

## Kada koristiti
Koristi ovaj skill kada korisnik traži scalping analizu.

## Pravila
- Fokus na M5 i M15 timeframe
- Tighter stop loss (max 15 pips)
- Quick profit targets (10-20 pips)
- Izbjegavaj volatile periode

## Indikatori
- EMA 8/21
- RSI sa oversold/overbought zonama
- Volume
```

## Dostupni skills

| Skill | Opis | Status |
|-------|------|--------|
| technical_analysis | Osnovna TA | Built-in |
| adversarial_thinking | Bull vs Bear | Built-in |
| risk_management | Risk pravila | Built-in |
| scalping | Scalping strategija | Custom |
| swing_trading | Swing trading | Custom |
| news_trading | Trading oko vijesti | Custom |

---

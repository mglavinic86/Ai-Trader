# Moja Risk Pravila

> Osobna pravila koja NIKADA ne smijem prekršiti.
> AI će me upozoriti ako pokušam.

---

## Zlatna Pravila

### 1. Risk Per Trade
- **NIKADA** više od 3% po tradeu
- Standardno: 1-2% ovisno o confidence-u
- Smanji na 0.5% ako nisam siguran

### 2. Daily Loss Limit
- **STOP** nakon 3% gubitka u danu
- Nema više tradinga do sutra
- Review što je pošlo po zlu
- *Auto-reset: UTC midnight*

### 3. Weekly Loss Limit
- **PAUSE** nakon 6% gubitka u tjednu
- Obvezna analiza svih tradeova
- Možda pauza do sljedećeg tjedna
- *Auto-reset: ponedjeljak UTC*

> **NOVO:** Sustav automatski prati i resetira daily/weekly P/L!

### 4. Position Sizing
```
Position Size = (Equity × Risk%) / (SL pips × pip value)
```
Nikad ručno povećavaj size!

---

## Kada NE TRADATI

- [ ] Umoran sam
- [ ] Ljut sam (revenge trading!)
- [ ] Pijem alkohol
- [ ] Major news za < 30 min
- [ ] Petak nakon 20:00 UTC
- [ ] Spread > 3 pips
- [ ] "Osjećam" da će ići gore/dolje (bez analize)

---

## Red Flags

Ako uhvatim sebe da mislim:
- "Ovaj put će biti drugačije" → STOP
- "Samo još jedan trade" → STOP
- "Nadoknadit ću gubitak" → STOP
- "100% sam siguran" → SMANJI RISK

---

## Pravila za Gubitke

1. **Prihvati gubitak** - dio je tradinga
2. **Analiziraj** - što je pošlo po zlu?
3. **Zapiši** - dodaj u lessons.md
4. **Nastavi** - ali ne isti dan ako > 2% loss

---

## Reward Rules

Kad sam profitabilan:
- Withdraw 20% profita mjesečno
- Ne povećavaj position size odmah
- Čekaj 3 mjeseca konzistentnosti

---

*Zadnje ažuriranje: 2026-01-31 (Session 11 - Security Fixes)*

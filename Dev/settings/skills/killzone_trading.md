# Skill: Killzone Trading

> Koristi ovaj skill za session-based trading strategije.

## Kada aktivirati

Aktiviraj kada korisnik kaze:
- "killzone analiza"
- "London session"
- "NY session"
- "Asian range"
- "session trading"

## Killzone Times (UTC)

| Session | Time | Best For |
|---------|------|----------|
| Asian | 00:00 - 07:00 | Range building (ne trguj) |
| London KZ | 08:00 - 11:00 | Asian sweep + reversal |
| Lunch | 11:00 - 13:00 | Avoid |
| NY KZ | 13:00 - 16:00 | Continuation or reversal |
| London Close | 15:00 - 17:00 | Potential reversals |

## Strategy 1: Asian Range Sweep

### Workflow
```
1. Oznaci Asian High/Low (00:00-07:00 UTC)
   |
2. Cekaj London Killzone (08:00-11:00)
   |
3. Gledaj sweep Asian H/L
   |
4. CISD + FVG confirmation
   |
5. Entry u suprotnom smjeru
```

### Rules
- Target: Suprotna strana Asian range ili PDH/PDL
- SL: Ispod/iznad sweep swing
- Best: First 2 hours of London

## Strategy 2: NY Continuation

### Workflow
```
1. Odredi HTF bias (Daily/H4)
   |
2. Gledaj London pullback u zonu
   |
3. NY Killzone start (13:00 UTC)
   |
4. BOS + FVG u smjeru biasa
   |
5. Entry on FVG
```

### Rules
- Trade u smjeru HTF trenda
- Target: PWH/PWL ili HTF liquidity
- SL: Ispod/iznad pullback zone

## Strategy 3: NY Reversal

### Workflow
```
1. London sweepne major liquidity (PDH/PDL)
   |
2. Trziste iscrpljeno
   |
3. NY Killzone CISD na M15
   |
4. FVG u reversal smjeru
   |
5. Entry, target suprotna liquidity
```

### Rules
- NE dogadja se svaki dan
- Zahtijeva liquidity sweep PRIJE
- Target: Suprotna liquidity

## Entry pravila

1. **Identificiraj Session**
   - London: Asian sweep opportunities
   - NY: Continuation ili reversal

2. **Oznaci Kljucne Razine**
   - Asian H/L
   - PDH/PDL
   - PWH/PWL

3. **Cekaj Confirmation**
   - CISD na LTF
   - FVG formacija
   - BOS u smjeru

4. **Entry**
   - Na FVG ili OB
   - SL izvan swinga
   - Target na liquidityu

## Exit pravila

- **Stop Loss:** Iznad/ispod sweep swing
- **Take Profit:** Opposite liquidity
- **R:R Minimum:** 1:2

## Timeframe

- **Setup:** H1, M30
- **Entry:** M15, M5
- **Management:** M5

## IZBJEGAVAJ

- Prvih 30 min svake sesije (spike)
- Lunch period (11:00-13:00 UTC)
- 15 min prije/poslije major news
- Trading Asian session (samo oznaci range)

## Risk Management

- Max 1% per killzone trade
- Max 1 trade per killzone
- Stop after 2 consecutive losses

## News Check

Uvijek provjeri economic calendar:
- NFP, FOMC, CPI = NO TRADE
- Medium impact = Caution
- No news = Normal trading

---

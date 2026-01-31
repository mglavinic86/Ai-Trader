# Session Trading Strategies

> Strategije prilagodjene specificnim trading sesijama.

## Trading Session Overview

### Session Times (UTC/GMT)

| Session | Time (UTC) | Characteristics |
|---------|------------|-----------------|
| Asian Session | 00:00 - 07:00 | Low volatility, range formation |
| London Killzone | 08:00 - 11:00 | High volatility, liquidity sweeps |
| NY Killzone | 13:00 - 16:00 | Continuation or reversal |
| London Close | 15:00 - 17:00 | Potential reversals |

---

## Strategy 1: Asian Range During London Killzone

### Why It Works

London sesije cesto sweepaju Asian likvidnost jer:
- Mnogi retail traderi stavljaju SL iznad Asian High i ispod Asian Low
- Algoritmi koriste London open da "pokupe" ovu likvidnost prije pravog poteza
- Asian range stvara jasan "liquidity frame" za London

### Step-by-Step Process

#### Step 1: Mark the Asian Range
- Oznaci **Asian High** i **Asian Low**
- To je tvoj "liquidity frame"

#### Step 2: Wait for London Killzone (08:00 - 11:00 UTC)
- Prvi sat Londona tipicno sweepne Asian likvidnost
- Najcesci scenarij: cijena probije Asian High ili Low, pa se vrati u suprotnom smjeru

#### Step 3: Look for Confirmation
Nakon uzimanja likvidnosti:
- **CISD** na LTF
- Formacija **FVG** ili **OB**
- Entry NAKON konfirmacije, nikada odmah na sweep

#### Step 4: Set Targets
- Target: **PDH/PDL** ili **suprotna strana Asian range-a**

---

## Strategy 2: New York Continuation

### Description
Jedna od najprofitabilnijih situacija kada NY sesija **nastavlja smjer HTF biasa**.

### Step-by-Step Process

#### Step 1: Analyze Higher Timeframe
- Check Weekly, Daily, or H4 for clear bias
- Identify key levels: PWH/PWL, PDH/PDL

#### Step 2: Identify H4 Zone
- Nadji FVG/OB zonu s koje je cijena prethodno napravila snazan potez
- To postaje tvoja zona interesa

#### Step 3: Monitor London Session
- Ako London napravi pullback u tvoju zonu, pripremi se za NY continuation

#### Step 4: Enter During NY Killzone
- Kada NY sesija pocne, trazi:
  - BOS u smjeru HTF biasa
  - FVG formaciju na M15 za entry

### Key Points
- NE pogadjaj reversale - slijedi HTF trend
- NY continuation je pridruživanje pokretu, ne predvidjanje

---

## Strategy 3: New York Reversal

### Description
NY Reversal se dogadja kada cijena promijeni smjer nakon London poteza.

### When It Happens
- NE dogadja se svaki dan
- Cesto kada:
  - Cijena dosegne zonu s HTF-a
  - Likvidnost je sweepnuta tijekom NY sesije
  - London iscrpi jedan smjer poteza

### Step-by-Step Process

#### Step 1: Identify Liquidity Sweep
- Tijekom London sesije, cijena sweepne kljucnu razinu (PDL/PDH)

#### Step 2: Recognize Exhaustion
- Nakon liquidity sweepa, trziste cesto nema vise "goriva" za nastavak

#### Step 3: Wait for NY Killzone Confirmation
- Gledaj **CISD** na M15
- Cekaj mali FVG u smjeru reversala

#### Step 4: Enter the Reversal
- Ulazi long/short based on reversal direction
- SL ispod/iznad swing low/high
- Target: suprotna likvidnost

---

## Session Trading Summary Table

| Strategy | Session | Setup | Entry Trigger | Target |
|----------|---------|-------|---------------|--------|
| Asian Range | London KZ | Asian H/L sweep | CISD + FVG/OB | Opposite side / PDH/PDL |
| NY Continuation | NY KZ | HTF trend + London pullback | BOS + FVG | PWH/PWL / HTF liquidity |
| NY Reversal | NY KZ | London liquidity sweep | CISD + FVG | Opposite liquidity |

---

## Best Times to Trade Each Strategy

| Strategy | Optimal Entry Window | Avoid |
|----------|---------------------|-------|
| Asian Range | 08:00 - 10:00 UTC | Trading Asian session itself |
| NY Continuation | 13:30 - 15:00 UTC | First 30 min of NY |
| NY Reversal | 14:00 - 16:00 UTC | Trading without liquidity sweep |

---

## News Impact Handling

### High-Impact News
- **Izbjegavaj trading 15-30 minuta prije i poslije** major vijesti
- NFP, FOMC, CPI mogu uzrokovati ekstremnu volatilnost

### Best Practice
- Check economic calendar before each session
- Mark news times on chart
- If major news during killzone, wait for price to settle

---

## Quick Reference: Killzone Times

```
Asian Session:     00:00 - 07:00 UTC (range building)
London Killzone:   08:00 - 11:00 UTC (liquidity sweep)
Lunch (low vol):   11:00 - 13:00 UTC (avoid)
NY Killzone:       13:00 - 16:00 UTC (continuation/reversal)
London Close:      15:00 - 17:00 UTC (potential reversals)
```

---

*Source: Session Trading by Luka Tatalovic*

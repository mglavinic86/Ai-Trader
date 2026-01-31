# Entry Models - ICT Trading Strategies

> Tri entry modela za precizne ulaze u trade.

## Prerequisites Before Using Any Entry Model

Prije primjene bilo kojeg entry modela, MORAS imati:

1. **Clear Bias (Direction)** - Odreden s viseg timeframe-a (H4/Daily/Weekly)
2. **Zone of Interest** - Identificirana zona (Liquidity, Order Block, FVG)
3. **Lower Timeframe Confirmation** - M5/M15 za precizan ulaz

### General Entry Rules

- Uvijek imaj definiran bias s HTF
- Nikada ne ulazi bez zone (OB/FVG/liquidity)
- Cekaj potvrdu na LTF
- SL iznad/ispod zone ili swing high/low
- Risk maximum 1% po trade-u
- Minimum 1:2 Risk-Reward ratio

---

## Entry Model 1: Liquidity Sweep + CISD + FVG

### Description
Najstrukturiraniji entry model koji kombinira liquidity sweep, CISD i FVG entry.

### Rules

1. **Wait for Zone** - Cijena mora doci do HTF zone interesa (FVG/Liquidity/OB)
2. **Liquidity Sweep** - Gledaj da cijena sweepne "najznacajniju" strukturu na LTF (M5/M15) unutar zone
3. **CISD Confirmation** - Nakon sweepa, cekaj CISD u smjeru tvog biasa
4. **Find FVG** - Nakon CISD-a, trazi FVG u smjeru breaka
5. **Entry** - Ulazi unutar FVG-a

### Stop Loss Placement
- SL ispod/iznad swinga koji je kreiran PRIJE breaka

### When to Use
- High probability setupi tijekom killzone-ova
- Kada imas jasan HTF bias i cijena ulazi u tvoju zonu
- Best during London and New York sessions

---

## Entry Model 2: Liquidity Sweep + iFVG (Inverse FVG)

### Description
Koristi inverse FVG koncept - kada cijena prodje kroz FVG i on postane support/resistance.

### Rules

1. **Wait for Zone** - Cijena mora doci u HTF zonu interesa
2. **Liquidity Sweep** - Na LTF, cekaj liquidity sweep
3. **Find FVG** - Nakon sweepa, identificiraj FVG
4. **Wait for Inverse** - Cekaj da cijena prodje kroz FVG i zatvori na drugoj strani (postaje inverse)
5. **Entry** - Ulazi kada svijeca zatvori iznad/ispod FVG-a ILI na novom FVG-u ako se formira

### Stop Loss Placement
- SL ispod/iznad swing high/low

### When to Use
- Kada zelis vise konfirmacije
- Nesto kasniji ulazi ali potencijalno veca win rate
- Dobro radi u ranging trzistima unutar HTF zona

---

## Entry Model 3: Liquidity Sweep + Order Block

### Description
Koristi Order Block kao entry point nakon CISD konfirmacije.

### Rules

1. **Wait for Zone** - Cijena mora doci do HTF zone interesa
2. **Liquidity Sweep** - Gledaj da cijena probije "najznacajniju" strukturu na LTF (M5/M15)
3. **CISD Confirmation** - Cekaj CISD u smjeru tvog biasa
4. **Find Order Block** - Nakon CISD-a, identificiraj OB u smjeru breaka
5. **Entry** - Ulazi na pocetku (edge) Order Blocka

### Stop Loss Placement
- SL ispod/iznad swinga kreiranog PRIJE breaka

### When to Use
- Kada se jasni OB formiraju nakon CISD-a
- Kada FVG nije vidljiv ili je prevelik
- Daje definiraniji entry point od FVG-a

---

## Model Comparison Table

| Feature | Entry Model 1 | Entry Model 2 | Entry Model 3 |
|---------|---------------|---------------|---------------|
| Entry Point | Within FVG | iFVG close / new FVG | Order Block edge |
| Confirmation | CISD + FVG | Liq Sweep + iFVG | CISD + OB |
| SL Placement | Below/above pre-break swing | Below/above swing H/L | Below/above pre-break swing |
| Speed | Medium | Slower (wait for inverse) | Medium |
| Risk | Standard | Lower (more confirmation) | Standard |
| Best For | Trending markets | Range/consolidation | Clear structure |

---

## Common Mistakes to Avoid

- Ulazak bez cekanja konfirmacije
- Ignoriranje HTF analize
- Tradanje svakog setupa bez konteksta
- Pomicanje stop lossa u nadi da ce se cijena vratiti

---

*Source: Entry Models by Luka Tatalovic*

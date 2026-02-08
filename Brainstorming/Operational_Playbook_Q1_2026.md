# AI Trader - Operativni Playbook (Veljaca - Travanj 2026)

> **Pocetno stanje:** Balance 48,517 EUR | Win Rate 5.1% | Service STOPPED | Dry Run TRUE
> **Cilj:** Stabilizirati sustav, dokazati profitabilnost, postepeno prelaziti na live

---

## FAZA 1: Ciscenje i Priprema (Tjedan 1-2)

### Tjedan 1 - Popravke

**Sto napraviti:**
- [ ] Ocistiti zombie trade iz DB-a (EUR_JPY LONG @ 183.785)
- [ ] Ukloniti BTCUSD iz aktivnih instrumenata (MT5 error "No price data")
- [ ] Pokrenuti Walk-Forward backtest na historical data (6 mjeseci)
- [ ] Zapisati backtest rezultate (Sharpe, drawdown, profit factor)
- [ ] Provjeriti da svi ISI testovi prolaze (42/42)
- [ ] Aktivirati Finnhub API key za economic calendar

**Instrumenti za Fazu 1-2:**
```
SAMO: EUR_USD, GBP_USD, XAU_USD
BEZ:  BTCUSD (dok se ne popravi MT5 data)
```

### Tjedan 2 - Dry Run Test

**Sto napraviti:**
- [ ] Pokrenuti sustav: dry_run = TRUE, service = RUNNING
- [ ] Pustiti da radi 5 punih trading dana (ponedjeljak-petak)
- [ ] NE DIRATI NISTA - samo promatrati
- [ ] Svaki dan zapisati: koliko signala, koliko APPROVE, koliko REJECT, koji instrumenti
- [ ] Na kraju tjedna: pregledati sve odluke u Decision Trail

**Dnevna rutina (5 min):**
```
Jutro (08:00):  Otvori Dashboard -> provjeri je li service RUNNING
                Pogledaj overnight aktivnost u Activity Log
Vecer (20:00):  Pogledaj dnevni summary na AutoTrading stranici
                Zapisi: broj signala / APPROVE / REJECT / razloge
```

---

## FAZA 2: Dry Run Promatranje (Tjedan 3-6)

### Cilj: Prikupiti 30+ dry-run signala za ISI kalibraciju

**Sustav radi NON-STOP (24/7 daemon mode):**
```bash
cd Dev
python run_daemon.py
```

Ali PAZI - ne svi sati su jednako bitni:

### Kada sustav TREBA raditi (najaktivnije sesije)

| Sesija | Vrijeme (CET) | Instrumenti | Kvaliteta |
|--------|---------------|-------------|-----------|
| **London Open** | 08:00 - 12:00 | EUR_USD, GBP_USD, XAU_USD | NAJBOLJA |
| **NY Overlap** | 14:00 - 17:00 | SVI | NAJBOLJA |
| London Close | 17:00 - 18:00 | EUR_USD, GBP_USD | Dobra |
| NY Close | 20:00 - 22:00 | XAU_USD | Srednja |
| Asian | 00:00 - 08:00 | XAU_USD (jedino) | Slaba |

**Preporuka:** Pusti daemon 24/7 - sustav sam detektira sesije i market regime.
Ne moras ga paliti/gasiti po sesijama. SMC pipeline vec ima session-aware logiku.

### Tjedni pregled (svaki petak, 15 min)

Otvori Dashboard i zapisi:

```
Tjedan: ___
Ukupno signala: ___
APPROVE:        ___
REJECT:         ___
Najbolji instrument: ___
Najcesci razlog odbijanja: ___
ISI Calibrator status: UNCALIBRATED / CALIBRATED (30+ trades?)
Sequence Tracker: koje faze se pojavljuju najcesce?
```

### Kad ZAUSTAVITI sustav odmah

- Dashboard pokazuje HEARTBEAT STALE (>2 min) - restartaj daemon
- Vidis iste errore koji se ponavljaju u logu - zaustavi i istrazi
- MT5 disconnected i ne reconnecta se automatski

### Sto NE raditi u Fazi 2

- NE mijenjati postavke (threshold, risk, R:R)
- NE ukljucivati live trading
- NE dodavati nove instrumente
- NE ignorirati Decision Trail - to su tvoji podaci za evaluaciju

---

## FAZA 3: Evaluacija i Odluka (Tjedan 7-8)

### Nakon 4 tjedna dry-run promatranja, odgovori na ova pitanja:

**Pitanje 1: Je li Calibrator kalibriran?**
- DA (30+ tradeova) -> nastavi na Fazu 4
- NE -> produzi Fazu 2 jos 2 tjedna

**Pitanje 2: Kakav je "virtualni" win rate dry-run signala?**
- > 40% -> ODLICNO, spreman za live
- 30-40% -> OK, ali trebas pregledati zasto gubici
- < 30% -> STOP. Treba istraziti sto ne valja prije live tradinga

**Pitanje 3: Koliko signala dnevno generira?**
- 0-1 -> Previse konzervativan, mozda smanjiti threshold na 70
- 2-4 -> IDEALNO
- 5+ -> Previse agresivan, povecati threshold na 80

**Pitanje 4: Koji instrument performira najbolje?**
- Fokusiraj se na 1-2 najbolja za pocetak live tradinga

### Ako su odgovori pozitivni -> prelazi na Fazu 4

---

## FAZA 4: Oprezni Live Trading (Tjedan 9-12)

### NAJVAZNIJI KORAK. Postepeno, oprezno.

### Tjedan 9-10: Mikro Live

```json
{
  "dry_run": false,
  "risk_per_trade_percent": 0.1,
  "max_trades_per_day": 1,
  "min_confidence_threshold": 80,
  "target_rr": 3.0,
  "instruments": ["EUR_USD"]
}
```

**Pravila:**
- SAMO 0.1% risk (umjesto 0.3%) - to je ~48 EUR po tradeu
- SAMO 1 trade dnevno
- SAMO EUR_USD (najlikvidniji, najmanji spread)
- Threshold 80 (samo najbolji signali)
- Svaki trade ODMAH pregledaj u Dashboardu

### Tjedan 11-12: Prosirenje (AKO je Tjedan 9-10 pozitivan)

```json
{
  "risk_per_trade_percent": 0.2,
  "max_trades_per_day": 2,
  "min_confidence_threshold": 78,
  "instruments": ["EUR_USD", "GBP_USD"]
}
```

**Kriterij za prosirenje:**
- Min 5 zatvorenih tradeova u Tjednu 9-10
- Win rate >= 40%
- Neto P/L >= 0 (barem break-even)

### Kad ODMAH ZAUSTAVITI live trading

| Situacija | Akcija |
|-----------|--------|
| 3 gubitka u nizu | Sustav automatski pauzira 30 min (cooldown) |
| Dnevni gubitak > 2% | ZAUSTAVI, pregled sutra |
| Tjedni gubitak > 4% | ZAUSTAVI, evaluacija cijelog sustava |
| MT5 error/disconnect | Zaustavi dok se ne rijesi |
| Neocekivani trade (krivi instrument, krivi smjer) | EMERGENCY STOP odmah |

---

## DNEVNA RUTINA (kad sustav radi live)

```
07:30  Provjeri: Je li daemon RUNNING? MT5 CONNECTED?
       Pogledaj overnight aktivnost
       Provjeri economic calendar - ima li HIGH IMPACT vijesti danas?

08:00  London Open - najaktivnije vrijeme pocinje
       Dashboard otvoren, prati AI Thinking panel

12:00  Provjera: koliko signala do sada? Ima li otvorenih pozicija?
       Ako ima otvorena pozicija - NE ZATVARAJ RUCNO (pusti sustav)

14:00  NY Overlap pocinje - drugi val aktivnosti
       Provjeri pozicije i P/L

17:00  London zatvara - pregled dnevnog uratka
       Zapisi rezultate

20:00  Vecernja provjera: sve pozicije zatvorene?
       Ako je petak - tjedni pregled
```

---

## TJEDNA RUTINA

### Petak navecer (20 min)

1. **Performance review**
   - Otvori Performance stranicu (10)
   - Zapisi: Win Rate, Profit Factor, avg R:R, ukupni P/L tjedna

2. **Decision Trail review**
   - Otvori AutoTrading -> Decision Trail
   - Pregledaj sve REJECT odluke - jesu li ispravne?
   - Pregledaj sve APPROVE+LOSS odluke - sto je poslo krivo?

3. **Lekcije tjedna**
   - Zapisi 1-3 kljucna zapazanja
   - Primjer: "XAU_USD ima previse false breakout-ova u Asian sesiji"

4. **Prilagodbe (AKO TREBA)**
   - NIKAD ne mijenjaj vise od 1 postavke tjedno
   - Male promjene: threshold +/-2, risk +/-0.05%
   - Zapisi sto si promijenio i zasto

---

## MJESECNA EVALUACIJA

### Kraj svakog mjeseca (45 min)

#### Metrke za pratiti

| Metrika | Cilj Mjesec 1 | Cilj Mjesec 2 | Cilj Mjesec 3 |
|---------|---------------|---------------|---------------|
| Win Rate | > 35% | > 40% | > 45% |
| Profit Factor | > 1.0 | > 1.3 | > 1.5 |
| Max Drawdown | < 3% | < 3% | < 3% |
| Avg R:R | > 2.0 | > 2.0 | > 2.5 |
| Tradeova/tjedan | 5-10 | 8-15 | 10-20 |
| Neto P/L | >= 0 | > 0 | > +500 EUR |

#### Odluke na kraju mjeseca

**Ako su ciljevi ispunjeni:**
- Povecaj risk za 0.05% (npr 0.1% -> 0.15% -> 0.2%)
- Dodaj 1 instrument
- Smanji threshold za 2 boda

**Ako ciljevi NISU ispunjeni:**
- Vrati se na konzervativnije postavke
- Analiziraj najcesce gubitke (instrument? sesija? regime?)
- Razmisli o tehnickim poboljsanjima (ML model, Volume Profile)

**Ako je mjesec u velikom minusu (>3% drawdown):**
- ZAUSTAVI live trading
- Vrati se na dry_run
- Pokreni novu rundu backtestinga
- Identificiraj root cause prije nastavka

---

## ZLATNA PRAVILA (na zid pored monitora)

1. **NIKAD ne povecavaj risk nakon gubitka** - to je kockanje, ne trading
2. **NIKAD ne zatvaraj trade rucno** jer "osjecas" da ce se okrenuti
3. **NIKAD ne mijenjaj vise od 1 postavke tjedno**
4. **UVIJEK pregledaj Decision Trail** - tvoji podaci su tvoj edge
5. **Dry run MORA biti pozitivan** prije live tradinga
6. **Gubitak je normalan** - 40% win rate je profitabilan s R:R 3.0
7. **Sustav radi za tebe, ne ti za sustav** - ne sjedi i zuris u chart
8. **Petak = review dan** - bez pregleda nema napretka
9. **Strpljenje** - 3 mjeseca je minimum za evaluaciju sustava
10. **Cilj nije 200 EUR/dan odmah** - cilj je KONZISTENTNOST

---

## POSTEPENA ESKALACIJA (pregled)

```
Tjedan 1-2:   Ciscenje + popravke + dry run test
Tjedan 3-6:   Dry run 24/7, promatranje, ISI kalibracija
Tjedan 7-8:   Evaluacija rezultata, odluka o live tradingu
Tjedan 9-10:  MIKRO LIVE (0.1% risk, 1 trade/dan, samo EUR_USD)
Tjedan 11-12: Prosirenje AKO pozitivno (0.2%, 2 trade/dan, +GBP_USD)
Mjesec 3:     Puni live (0.3%, 2 trade/dan, 3 instrumenta)
Mjesec 4+:    Optimizacija, FTMO razmatranje
```

---

## EMERGENCY KONTAKTI (sto raditi kad nesto ne valja)

| Problem | Rjesenje |
|---------|----------|
| Daemon ne radi | `cd Dev && python run_daemon.py` |
| MT5 disconnect | Provjeri internet, restartaj MT5 terminal |
| Trade otvoren a ne bi trebao biti | Dashboard -> Positions -> zatvori rucno |
| Sustav trguje previse | Povecaj threshold za 5 bodova |
| Sustav uopce ne trguje | Smanji threshold za 3 boda, provjeri spread |
| Nepoznati error u logu | Zaustavi sustav, pokreni Claude sesiju za debug |
| Veliki gubitak (>2% u danu) | Emergency stop: zatvori sve pozicije rucno |

---

*Playbook kreiran: 2026-02-07*
*Sljedeci review: Kraj veljace 2026*
*Napomena: Ovaj dokument je ZIVI dokument - azuriraj ga svaki mjesec*

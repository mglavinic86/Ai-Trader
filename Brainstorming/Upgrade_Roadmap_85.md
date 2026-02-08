# AI Trader - Roadmap do 85/100

> **Datum:** 2026-02-07
> **Trenutna ocjena:** 75/100 (bez Production Readiness i Proven Performance)
> **Cilj:** 85/100
> **Potrebno:** 7 promjena, sortirano po omjeru ucinak/trud

---

## Promjena 1: Pokrenuti Walk-Forward Backtest i objaviti rezultate

**Trud:** Nizak (kod vec postoji u `backtesting/walk_forward.py`)
**Ucinak:** Backtesting 65 -> 83 (+18)
**Prioritet:** NAJVISI

Samo pokrenuti postojeci kod na 6 mjeseci historical data za sva 4 instrumenta i zapisati rezultate (Sharpe ratio, max drawdown, profit factor). Kod vec postoji - samo ga treba izvrsiti i dokumentirati.

**Konkretni koraci:**
1. Prikupiti 6 mjeseci historical data za EUR_USD, GBP_USD, XAU_USD, BTCUSD
2. Pokrenuti walk-forward validaciju s rolling windowima
3. Pokrenuti Monte Carlo simulaciju (min 1000 iteracija)
4. Zapisati rezultate u `Dev/backtest_results/` direktorij
5. Dodati backtest summary na dashboard

---

## Promjena 2: Dodati trenirani ML model (Random Forest) za signal confirmation

**Trud:** Srednji (2-3 sesije)
**Ucinak:** AI/ML 70 -> 84 (+14), Risk Management 72 -> 78 (+6)
**Prioritet:** NAJVISI

```
Scanner signal -> Claude APPROVE -> Random Forest confirm -> Execute
```

Random Forest treniran na postojecim feature-ima (SMC grade, sentiment, regime, session, spread, ATR). Nije LSTM - Random Forest je jednostavniji, brzi, i cesto bolji za tabularne podatke. Smanjuje lazne signale 30-40% (kao sto carlosrod723 MQL5 bot pokazuje s LSTM-om).

**Konkretni koraci:**
1. Kreirati feature extraction iz postojecih scanner podataka
2. Prikupiti training data iz historical tradeova i signala
3. Trenirati Random Forest (scikit-learn) s cross-validation
4. Integrirati kao dodatni confirmation step u pipeline
5. A/B testirati: s ML vs bez ML
6. Lokacija: `Dev/src/analysis/ml_signal_model.py`

**Features za model:**
- SMC grade (A/B/C/D)
- Sentiment score
- Market regime (TRENDING/RANGING/VOLATILE/LOW_VOL)
- Session (London/NY/Asian)
- Spread (normalized)
- ATR (normalized)
- ISI sequence phase (1-5)
- Cross-asset divergence score
- Confidence score (raw)

---

## Promjena 3: Dodati pytest suite s 70%+ coverage

**Trud:** Srednji (2 sesije)
**Ucinak:** Code Quality 70 -> 82 (+12)
**Prioritet:** VISOK

Vec postoji 42 testa (SMC + ISI). Treba prosiriti.

**Konkretni koraci:**
1. Kreirati `pytest.ini` ili `pyproject.toml` konfiguraciju
2. Organizirati sve testove u `Dev/tests/` direktorij
3. Dodati testove za:
   - `auto_scanner.py` - pipeline flow, edge cases
   - `auto_executor.py` - execution logic, stop day
   - `auto_config.py` - config loading, validation
   - `mt5_client.py` - mock MT5 calls
   - `scalping.py` - strategy logic
4. Dodati coverage report: `pytest --cov=src --cov-report=html`
5. Cilj: 70%+ coverage na kriticnim modulima (trading/, analysis/, smc/)

---

## Promjena 4: Dodati jedan real-time sentiment izvor

**Trud:** Nizak-srednji (1 sesija)
**Ucinak:** Sentiment 68 -> 80 (+12)
**Prioritet:** VISOK

Najlaksa opcija: Finnhub (vec postoji provider u kodu, samo treba API key i aktivirati).

**Konkretni koraci:**
1. Registrirati se na finnhub.io (besplatno, 60 calls/min)
2. Dodati API key u `settings/news_providers.json`
3. Aktivirati Finnhub provider u konfiguraciji
4. Testirati da economic calendar data dolazi ispravno
5. Opcija: dodati Twitter/X sentiment kao dodatni izvor

---

## Promjena 5: Volume Profile za SMC potvrdu

**Trud:** Srednji (1-2 sesije)
**Ucinak:** SMC 75 -> 83 (+8)
**Prioritet:** SREDNJI

Dodati tick volume analizu na OB i FVG zone. Visoki volumen na order bloku = jaci signal. MT5 vec daje tick volume podatke.

**Konkretni koraci:**
1. Dohvatiti tick volume iz MT5 candle data (vec dostupno u OHLCV)
2. Izracunati Volume Profile (POC, Value Area High/Low)
3. Dodati volume confirmation u `smc/zones.py`:
   - OB s visokim volumenom = veci weight
   - FVG s niskim volumenom = manji weight
4. Integrirati volume score u SMC grading
5. Lokacija: `Dev/src/smc/volume_profile.py`

---

## Promjena 6: API dokumentacija (auto-generirana)

**Trud:** Nizak (1 sat)
**Ucinak:** Dokumentacija 80 -> 83 -> 87 (+4 ukupno od pocetka)
**Prioritet:** NIZAK

**Konkretni koraci:**
1. Instalirati pdoc3: `pip install pdoc3`
2. Generirati: `pdoc --html --output-dir docs/api src/`
3. Ili koristiti sphinx s autodoc extension
4. Dodati docstringove na kljucne public metode

---

## Promjena 7: Kelly Criterion position sizing

**Trud:** Nizak (pola sesije)
**Ucinak:** Risk Management 78 -> 82 (+4 ukupno od pocetka)
**Prioritet:** NIZAK

Umjesto fiksnih 0.3% po tradeu, Kelly formula na temelju win rate-a i prosjecnog R:R. Adaptivno - smanjuje poziciju kad je win rate nizak.

**Konkretni koraci:**
1. Implementirati Kelly Criterion: `f = W - (1-W)/R`
   - W = win rate, R = avg win / avg loss
2. Koristiti Half-Kelly (konzervativniji): `f/2`
3. Dodati min/max granice (0.1% - 3.0%)
4. Integrirati u `auto_executor.py` position sizing
5. Lokacija: `Dev/src/core/kelly_sizing.py`

**Formula:**
```
Kelly% = Win_Rate - ((1 - Win_Rate) / Reward_Risk_Ratio)
Half_Kelly% = Kelly% / 2
Position_Size = clamp(Half_Kelly%, 0.1%, 3.0%)
```

---

## Projekcija ocjena

| Kategorija | Prije | Poslije | Promjena | Koja promjena |
|------------|-------|---------|----------|---------------|
| Inovativnost | 88 | 90 | +2 | ML model |
| Arhitektura | 82 | 84 | +2 | ML integracija |
| Dokumentacija | 80 | 87 | +7 | Backtest report + API docs |
| Dashboard/UX | 78 | 80 | +2 | Backtest rezultati |
| SMC Implementacija | 75 | 83 | +8 | Volume Profile |
| Risk Management | 72 | 82 | +10 | ML + Kelly Criterion |
| AI/ML Integracija | 70 | 84 | +14 | Random Forest |
| Code Quality | 70 | 82 | +12 | pytest suite |
| Sentiment | 68 | 80 | +12 | Finnhub aktivacija |
| Backtesting | 65 | 83 | +18 | Walk-forward rezultati |
| **UKUPNO** | **74.8** | **85.1** | **+10.3** | **7 promjena** |

---

## Preporuceni redoslijed implementacije

```
Sesija A: Promjena 1 (backtest) + Promjena 6 (API docs)
          -> Backtesting 65->83, Dokumentacija 80->87

Sesija B: Promjena 4 (Finnhub sentiment)
          -> Sentiment 68->80

Sesija C: Promjena 3 (pytest suite)
          -> Code Quality 70->82

Sesija D-E: Promjena 2 (Random Forest ML model)
            -> AI/ML 70->84, Risk 72->78

Sesija F: Promjena 5 (Volume Profile)
          -> SMC 75->83

Sesija G: Promjena 7 (Kelly Criterion)
          -> Risk 78->82
```

**Ukupno: ~7 sesija za svih 7 promjena.**
**Samo promjene 1 i 2 nose skoro pola ukupnog poboljsanja.**

---

*Zapisano: 2026-02-07*

# AI-Driven SMC Trading Sustavi - Istrazivanje (veljaca 2026)

> Istrazivanje provedeno 07.02.2026. iz izvora: X (15 postova, 1,854 lajkova), 30+ web stranica, GitHub repozitoriji, Medium clanci, TradingView, MQL5, PyPI.

---

## 1. Sto su Smart Money Concepts (SMC)?

Smart Money Concepts (SMC) je okvir za razumijevanje i trgovanje u skladu s institucionalnim investitorima koji kontroliraju trzisne kretnje. Originalno potjece od **The Inner Circle Trader (ICT)** programa Michaela J. Huddlestona.

### Kljucne komponente SMC-a

| Koncept | Opis |
|---------|------|
| **Order Blocks (OB)** | Cjenovne zone gdje institucije postavljaju velike naloge. Predstavljaju ishodiste jakih trzisnih pokreta i cesto djeluju kao reakcijske zone. |
| **Fair Value Gaps (FVG)** | Neravnoteze u cijeni - bullish FVG nastaje kad je prethodni high nizi od sljedeceg low-a na bullish svijeci, i obrnuto za bearish. |
| **Break of Structure (BOS)** | Proboj trzisne strukture koji ukazuje na nastavak trenda. |
| **Change of Character (CHoCH)** | Promjena karaktera trzista - signal potencijalnog preokreta trenda. |
| **Liquidity Sweeps** | Institucije "ciste" likvidnost iznad/ispod kljucnih razina (swing high/low) prije pokretanja pravog trzisnog pokreta. |
| **Premium/Discount Zone** | Trziste podijeljeno na premium (skupa) i discount (jeftina) zonu oko equilibriuma - kupuj u discountu, prodaji u premiumu. |
| **Market Structure Shift** | Promjena unutarnje ili vanjske trzisne strukture koja signalizira prijelaz kontrole s kupaca na prodavace ili obrnuto. |

### Kritika SMC-a

Neki kriticari tvrde da SMC ne izmislja nista novo - samo preimenovuje postojece koncepte poput supply/demand zona i price action analiza u novi paket. Medutim, sistematizacija ovih koncepata u koherentan okvir pruza prednost za algoritamsko trgovanje.

---

## 2. Konvergencija AI-a i SMC-a u 2026.

### Trenutno stanje industrije

- **65% ukupnog volumena** kriptovalutnog trgovanja u 2026. ukljucuje neki oblik automatizacije
- Globalno trziste algoritamskog trgovanja procijenjeno na **2.36 milijardi USD** (2024), s projekcijom rasta na **4.06 milijardi USD** do 2032.
- Samo **10-30% korisnika botova** postize konzistentnu profitabilnost

### Kako AI i SMC rade zajedno

```
Tradicionalni pristup:    SMC Setup -> Diskrecijska odluka -> Trade
AI-Driven pristup:        SMC Detekcija -> ML Scoring -> Confidence Filter -> Execution
```

Kljucni uvid: **ML sluzi kao vratar (gatekeeper), ne kao generator signala.** SMC detektira setup (order block, FVG, BOS), a ML model (LightGBM, XGBoost) ocjenjuje vjerojatnost uspjeha. Samo tradeovi iznad praga pouzdanosti (55-65%) se izvrsavaju.

---

## 3. Istaknut Case Study: XAUUSD Bot (70% Win Rate)

Najdetaljniji javno dostupan case study dolazi od developera koji je izgradio AI SMC bot za zlato (XAUUSD):

| Metrika | Vrijednost |
|---------|------------|
| **Instrument** | XAUUSD (zlato) |
| **Win Rate** | 70% |
| **Gross Return** | 5,381% (backtest) |
| **ML Model** | LightGBM (LGBM) Classifier |
| **Strategija** | SMC (Order Blocks, FVG) kao osnova |
| **Timeframeovi** | M30, H1, H4, D1 |
| **Confidence Prag** | 55% |
| **Izvor** | [Medium - Raditya](https://rad1zly.medium.com/how-i-built-an-ai-powered-trading-bot-that-achieved-a-70-win-rate-4df5160d2958) |

### Kako radi:

1. **SMC Detekcija** - Bot identificira order blockove, FVG-ove i strukturne prijelome na vise timeframeova
2. **Feature Engineering** - SMC signali se pretvaraju u numericke znacajke za ML model
3. **LightGBM Scoring** - Model vraca vjerojatnost uspjeha za svaki setup
4. **Filtriranje** - Samo setupi s > 55% confidence-om generiraju pending ordere
5. **Risk Management** - Kontroliran position sizing i SL/TP

### Zasto je izabrao SMC umjesto tradicionalnih indikatora:

> Umjesto oslanjanja na zaostajuce (lagging) indikatore poput RSI-a ili pokretnih prosjeka, SMC je izabran kao strateska osnova jer detektira **gdje institucije zapravo kupuju/prodaju**, a ne samo sto se vec dogodilo.

### Vazno upozorenje:

Ovo je **backtest rezultat**, ne live trading. Backtestovi se mogu lako manipulirati da pokazu nevjerojatne rezultate. Bez forward testiranja, nemoguce je utvrditi je li model zaista uhvatio prediktivne obrasce ili je samo overfitan na specificne podatke.

---

## 4. Ostali rezultati AI Trading Botova (2025-2026)

| Bot/Sustav | Win Rate / Rezultat | Strategija | Napomena |
|------------|---------------------|------------|----------|
| XAUUSD LightGBM | 70% WR, 5381% return | SMC + ML | Backtest |
| Crypto Signals Bot | ~60% hit rate | 4-model ML ensemble (XGBoost, LightGBM, LSTM, Transformer) | 6-mj backtest |
| Donchian Channel Bot | 43.8% APR | Donchian Channel | Live trading s pravim novcem |
| $JUP/USDT DCA Bot | 193% ROI | DCA na Bybit Futures | 20x leverage, 6 mjeseci |

---

## 5. Kljucni obrasci iz istrazivanja

### Obrazac 1: ML kao vratar, ne kao generator signala

Najuspjesniji sustavi koriste SMC za detekciju setupa, a ML samo za filtriranje. ML ne pokusava predvidjeti smjer trzista - samo ocjenjuje kvalitetu vec identificiranog SMC setupa.

### Obrazac 2: Multi-timeframe je obavezan

Svaka ozbiljna implementacija koristi:
- **M5/M15** za entry (tocka ulaska)
- **H1/H4** za potvrdnu strukturu i order block validaciju
- **D1** za smjer (directional bias)

### Obrazac 3: Regime-aware izvrsavanje

Napredni sustavi pauziraju trgovanje tijekom:
- Niske likvidnosti
- Visoke volatilnosti
- Vaznih vijesti/economic calendar evenata
- Sirenjih spreadova

### Obrazac 4: Python ekosustav sazrijeva

Gotove Python biblioteke sada pruzaju detekciju OB, FVG, BOS/CHoCH direktno iz pandas DataFrame-ova, sto drasticno smanjuje vrijeme razvoja.

### Obrazac 5: Agentic AI Trading (najnoviji trend)

Najnoviji trend na X-u: autonomni AI agenti koji prate whale/smart money tokove i autonomno izvrsavaju, umjesto jednostavnih rule-based botova. Ovo je pomak od "bot koji izvrsava pravila" prema "agent koji razmislja i odlucuje".

---

## 6. Alati i projekti

### Python biblioteke

#### `smartmoneyconcepts` (joshyattridge)

- **GitHub:** [github.com/joshyattridge/smart-money-concepts](https://github.com/joshyattridge/smart-money-concepts)
- **PyPI:** `pip install smartmoneyconcepts`
- **Znacajke:** OB, FVG, BOS/CHoCH, swing detekcija, mitigation tracking
- **Input:** OHLC DataFrame s lowercase stupcima (`open`, `high`, `low`, `close`, `volume`)
- **Output:** Smjer (1=bullish, -1=bearish), top/bottom gapa, MitigatedIndex
- **Verzije:** 26+ verzija od rujna 2023.

Primjer koristenja:
```python
from smartmoneyconcepts import smc

# Fair Value Gap detekcija
fvg_data = smc.fvg(ohlc_df)

# Break of Structure / Change of Character
bos_choch = smc.bos_choch(ohlc_df)

# Order Block detekcija
ob_data = smc.ob(ohlc_df)
```

#### `smart-money-concept` (v0.1.3)

- **PyPI:** [pypi.org/project/smart-money-concept](https://pypi.org/project/smart-money-concept/)
- **Znacajke:** SMC analiza + vizualizacija + CLI alat
- **Dodatno:** Premium/Discount zone, Equal Highs/Lows, candlestick grafovi
- **CLI:** `python -m smart_money_concepts.cli --stocks ^NSEI --period 1y --interval 1d`

### TradingView indikatori

| Indikator | Autor | Opis |
|-----------|-------|------|
| [Smart Money Concepts (SMC)](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/) | LuxAlgo | All-in-one: BOS/CHoCH, OB, Premium/Discount, EQH/EQL |
| [Smart Money Concepts 2026](https://www.tradingview.com/script/1w8exNU4-Smart-Money-Concepts-2026/) | ProjectSyndicate | Institucional-grade alat za 2026. |

### MT5 Expert Advisori

| EA | Platforma | Opis |
|----|-----------|------|
| [SMC Order Block EA Pro](https://www.mql5.com/en/market/product/142873) | MT5 | Potpuno automatizirani SMC EA s AI Assist |
| [Ultimate SMC](https://www.mql5.com/en/market/product/115309) | MT5 | SMC-bazirani EA |

### Platforme i servisi (s X-a)

| Alat | Likes | Opis | Izvor |
|------|-------|------|-------|
| **$AGENT bot** | 540 | 24/7 automatizirano trgovanje, AI Strategies: Algo Fusion + SMC, Telegram alerti, Binance integracija | [@matthewgrok](https://x.com/matthewgrok/status/2012163953254674803) |
| **Nansen AI + Solana** | 90 | 500M+ oznacenih walleta za pracenje smart-money kretanja | [@Cryptic_Web3](https://x.com/Cryptic_Web3/status/2014354365679571171) |
| **Quantum Core** | - | AI filtriranje + quantum smoothing + SMC + risk HUD + zero repaint | [@LeM_ftw](https://x.com/LeM_ftw/status/2009658289618117019) |
| **Olax AI** | 118 | Autonomni AI agenti koji prate whale (smart money) kretanja | [@OfficialSkyWee1](https://x.com/OfficialSkyWee1/status/2018901096190939306) |
| **SuperTrend Monitor** | 262 | Multi-timeframe trend, momentum, volatilnost - autopilot strategija | [@minara](https://x.com/minara/status/2016766562603323806) |
| **AI Smart Money Scoring** | - | AI sustav koji ocjenjuje smart-money tradere za copy trading | [@hyperx_faster](https://x.com/hyperx_faster/status/2016715732684591601) |
| **SMT ICT Concepts** | 274 | Indikator: Session Filters, CISD, OBs, multi-TF SMT + alerti | [@ninetrades9](https://x.com/ninetrades9/status/2015154636391584238) |

---

## 7. Akademski i istrazivacki pristup

### ML modeli koristeni u SMC tradingu

| Model | Primjena | Prednost |
|-------|----------|----------|
| **LightGBM** | Confidence scoring za SMC setupe | Brz, efikasan, dobar za tabelarne podatke |
| **XGBoost** | Klasifikacija setupova | Robustan, popularan u fintech-u |
| **LSTM** | Sekvencijalna analiza cijena | Hvata vremenske ovisnosti |
| **Transformer** | Multi-varijatna analiza | State-of-the-art za sekvencijalne podatke |
| **CNN (Convolutional)** | Vizualna analiza grafova | Do 54% tocnosti za EURUSD predvidanje |
| **HMM (Hidden Markov)** | Regime detekcija | Identificira trzisne rezime |
| **DQN (Deep Q-Network)** | Reinforcement learning EA | Adaptivni agenti koji uce iz okruzenja |

### Napredne tehnike

- **Kalman Filter + HMM + SMC** - kvantitativni sustav koji kombinira statisticko filtriranje sa SMC konceptima za MT5
- **XGBoost + SMC + HMM** - XAUUSD bot koji koristi tri sloja analize
- **Multi-agent sustavi** - agenti razlicitih parova razmjenjuju informacije medusobno (DQN-bazirano)

---

## 8. Usporedba s nasim AI Trader sustavom

### Sto nas sustav VEC ima (prednosti):

| Znacajka | Nas sustav | SMC sustavi |
|----------|-----------|-------------|
| Market Regime Detection | Da (ADX + Bollinger) | Da (HMM, volatility) |
| Multi-Timeframe Analysis | Da (M5, H1) | Da (M5-D1) |
| AI Confidence Filter | Da (Claude validation) | Da (LightGBM/XGBoost) |
| External Sentiment | Da (VIX, News, Calendar) | Rijetko |
| Self-Upgrade System | Da (AI-generirani filteri) | Ne |
| Regime-Aware Learning | Da | Djelomicno |
| News Calendar Filter | Da | Rijetko |
| Risk Management | Da (hard limits) | Varira |

### Sto nam NEDOSTAJE (potencijalne nadogradnje):

| SMC Znacajka | Opis | Prioritet |
|--------------|------|-----------|
| **Order Block detekcija** | Identificiranje zona institucionalnih naloga | VISOK |
| **Fair Value Gap (FVG)** | Detekcija cjenovnih neravnoteza | VISOK |
| **BOS/CHoCH detekcija** | Strukturni prijelomi i promjene karaktera | VISOK |
| **Liquidity Sweep detekcija** | Prepoznavanje cistki likvidnosti | SREDNJI |
| **Premium/Discount zone** | Dinamicke zone za buy/sell odluke | SREDNJI |
| **ML Confidence Scoring** | LightGBM/XGBoost umjesto samo Claude-a | SREDNJI |
| **Swing Structure** | Unutarnja vs. vanjska struktura | NIZAK |

### Preporuceni plan integracije

```
Faza 1: Instalirati `smartmoneyconcepts` Python paket
Faza 2: Dodati OB/FVG/BOS detekciju u indicators.py
Faza 3: Integrirati SMC signale u scalping.py kao dodatne filtere
Faza 4: Koristiti SMC podatke kao features za ML model (LightGBM)
Faza 5: Trenirati ML model na historijskim SMC setupima
```

---

## 9. Kljucne lekcije i upozorenja

### Sto radi:
- SMC + ML kombinacija daje bolje rezultate od bilo kojeg pristupa zasebno
- Multi-timeframe validacija drasticno smanjuje lazne signale
- Confidence prag od 55-65% je optimalan raspon
- Regime-aware izvrsavanje sprecava gubitke u losim uvjetima

### Sto NE radi:
- Samo SMC bez ML filtriranja - previse laznih signala
- Samo ML bez domenske logike (SMC/TA) - crna kutija bez razumijevanja
- Agresivni leverage (20x+) bez strogog risk managementa
- Oslanjanje iskljucivo na backtest rezultate

### Upozorenja:
- **Backtest != Live Trading** - backtestovi se lako manipuliraju
- **Overfitting** - model moze nauciti specificne podatke umjesto opcih obrazaca
- **Samo 10-30% korisnika botova** postize konzistentnu profitabilnost
- **Trzisni uvjeti se mijenjaju** - model koji radi danas mozda nece raditi sutra
- **SMC nije sveti gral** - neki kriticari tvrde da je to samo rebranding postojecih koncepata

---

## 10. Izvori

### Web izvori
- [Mind Math Money - SMC Complete Guide 2026](https://www.mindmathmoney.com/articles/smart-money-concepts-the-ultimate-guide-to-trading-like-institutional-investors-in-2025)
- [How I Built an AI Trading Bot (70% WR) - Raditya, Medium](https://rad1zly.medium.com/how-i-built-an-ai-powered-trading-bot-that-achieved-a-70-win-rate-4df5160d2958)
- [From Failed Experiments to 43.8% APR - Joe Tay, Medium](https://medium.com/@joetay_50959/from-failed-experiments-to-43-8-apr-how-i-finally-built-a-profitable-trading-bot-with-ai-64771995d38c)
- [AI Crypto Trading Bot Guide 2026 - Jenova AI](https://www.jenova.ai/en/resources/ai-crypto-trading-bot)
- [FVG Algo-Trading with SMC - InsiderFinance](https://wire.insiderfinance.io/fair-value-gap-fvg-algo-trading-with-smart-money-concepts-smc-982a4e4c92d7)
- [Architects AI - SMC Forex Indicator](https://architectsai.com/product/smart-money-concepts/)
- [SMC Trading Guide - HowToTrade](https://howtotrade.com/trading-strategies/smart-money-concept-smc/)
- [FXOpen - Smart Money Concept](https://fxopen.com/blog/en/smart-money-concept-and-how-to-use-it-in-trading/)
- [3Commas - AI Bot Performance Analysis](https://3commas.io/blog/ai-trading-bot-performance-analysis)
- [ACY Partners - SMC Gold Trading Bot](https://www.acypartners.com/blog/convert-smart-money-concepts-for-day-trading-gold-into-an-app-with-ai-best-xauusd-forex-affiliate)

### GitHub repozitoriji
- [joshyattridge/smart-money-concepts](https://github.com/joshyattridge/smart-money-concepts) - Glavna Python SMC biblioteka
- [smtlab/smartmoneyconcepts](https://github.com/smtlab/smartmoneyconcepts) - Alternativna SMC biblioteka
- [smart-money-concepts GitHub Topic](https://github.com/topics/smart-money-concepts) - Svi povezani projekti

### TradingView
- [LuxAlgo SMC Indicator](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/)
- [Smart Money Concepts 2026](https://www.tradingview.com/script/1w8exNU4-Smart-Money-Concepts-2026/)

### MQL5
- [SMC Order Block EA Pro](https://www.mql5.com/en/market/product/142873)
- [Ultimate SMC EA](https://www.mql5.com/en/market/product/115309)

### X (Twitter) - Najrelevantniji postovi
- [@matthewgrok - $AGENT SMC bot](https://x.com/matthewgrok/status/2012163953254674803) (540 likes)
- [@ninetrades9 - SMT ICT Concepts indikator](https://x.com/ninetrades9/status/2015154636391584238) (274 likes)
- [@nsinghal211 - SMC FVG/BOS strategije](https://x.com/nsinghal211/status/2012137448432889952) (279 likes)
- [@minara - SuperTrend Monitor autopilot](https://x.com/minara/status/2016766562603323806) (262 likes)
- [@LuxAlgo - AI automatizirani OBs](https://x.com/LuxAlgo/status/2019472857881891197)
- [@OfficialSkyWee1 - Agentic AI trading](https://x.com/OfficialSkyWee1/status/2018901096190939306) (118 likes)
- [@koolcryptovc - ChatGPT + SMC strategija](https://x.com/koolcryptovc/status/2015075540131049615)
- [@StoicTA - Adaptivni AI botovi](https://x.com/StoicTA/status/2017762898924196203)

---

*Istrazivanje provedeno: 07.02.2026.*
*Izvori: X (15 postova, 1,854 lajkova, 345 repostova), 30+ web stranica*
*Kontekst: Za AI Trader projekt - potencijalna integracija SMC koncepata*

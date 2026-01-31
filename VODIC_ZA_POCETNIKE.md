# AI Trader - Vodič za Početnike

> **Ovaj dokument objašnjava što je AI Trader, kako radi i kako se koristi - bez tehničkog žargona.**

---

## Što je AI Trader?

Zamislite da imate osobnog financijskog savjetnika koji:
- Prati tržište valuta **24 sata dnevno, 5 dana u tjednu**
- Analizira stotine podataka u sekundi
- Nikad nije umoran, ljut ili emocionalan
- Uvijek poštuje pravila upravljanja rizikom
- **Ali vas pita za dopuštenje prije svakog ulaganja**

To je AI Trader - računalni program koji koristi **umjetnu inteligenciju** za analizu tržišta valuta i predlaganje ulaganja.

---

## Što je Forex Trading?

### Jednostavno objašnjenje

**Forex** (Foreign Exchange) je kupnja i prodaja valuta.

Zamislite da idete na put u Ameriku:
1. U mjenjačnici date **100 EUR** i dobijete **108 USD** (tečaj 1.08)
2. Tjedan dana kasnije, tečaj se promijeni na **1.10**
3. Vaših 108 USD sada vrijedi samo **98 EUR**
4. Izgubili ste 2 EUR zbog promjene tečaja

Forex trading je **namjerno** kupovanje i prodavanje valuta kako biste zaradili na tim promjenama tečaja - ali u puno većim iznosima i s puno bržim reakcijama.

### Kako se zarađuje?

| Scenarij | Što radite | Kad zarađujete |
|----------|-----------|----------------|
| Mislite da će EUR ojačati | Kupujete EUR (prodajete USD) | Kad EUR poraste |
| Mislite da će EUR oslabiti | Prodajete EUR (kupujete USD) | Kad EUR padne |

**Primjer:**
- Kupite EUR po cijeni 1.0800 (1 EUR = 1.08 USD)
- Cijena poraste na 1.0850
- Prodajete i zaradite razliku: **50 "pipsa"** (0.0050)
- Na ulog od 10.000 EUR, to je oko **50 USD** zarade

---

## Zašto koristiti AI umjesto tradati sam?

### Problemi s ručnim tradingom

| Problem | Primjer |
|---------|---------|
| **Emocije** | Strah i pohlepa vode do loših odluka |
| **Umor** | Tržište radi 24h, vi ne možete |
| **Disciplina** | Teško je poštivati pravila kad gubite |
| **Brzina** | Prilike prolaze za sekunde |
| **Znanje** | Treba analizirati puno podataka |

### Što AI radi bolje

| Prednost | Objašnjenje |
|----------|-------------|
| **Bez emocija** | Ne osjeća strah ni pohlepu |
| **Uvijek budan** | Prati tržište non-stop |
| **100% disciplina** | Uvijek poštuje pravila rizika |
| **Brza analiza** | Analizira stotine podataka u sekundi |
| **Objektivnost** | Gleda samo činjenice, ne "osjećaje" |

### Što AI NE radi

- **Ne donosi konačne odluke sam** - uvijek pita vas za odobrenje
- **Ne jamči zaradu** - trading uvijek nosi rizik gubitka
- **Ne može predvidjeti budućnost** - samo analizira vjerojatnosti

---

## Kako AI Trader funkcionira?

### Korak po korak

```
┌─────────────────────────────────────────────────────────┐
│                    KAKO AI TRADER RADI                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   1. PRIKUPLJANJE PODATAKA                              │
│      └── AI prikuplja cijene valuta u realnom vremenu   │
│                         ▼                                │
│   2. TEHNIČKA ANALIZA                                   │
│      └── Analizira grafikone, trendove, pokazatelje     │
│                         ▼                                │
│   3. PROVJERA "ZA I PROTIV"                             │
│      └── Generira argumente ZA i PROTIV ulaganja        │
│                         ▼                                │
│   4. IZRAČUN POVJERENJA                                 │
│      └── Daje ocjenu od 0-100% koliko je siguran        │
│                         ▼                                │
│   5. PROVJERA RIZIKA                                    │
│      └── Provjerava smije li se uopće tradati           │
│                         ▼                                │
│   6. PREPORUKA KORISNIKU                                │
│      └── Pokazuje analizu i pita: "Želite li tradati?"  │
│                         ▼                                │
│   7. ČEKANJE VAŠEG ODOBRENJA                            │
│      └── Vi odlučujete: DA ili NE                       │
│                         ▼                                │
│   8. IZVRŠENJE (ako odobrite)                           │
│      └── AI izvršava trade i prati ga                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Što je "Povjerenje" (Confidence)?

AI daje ocjenu od **0 do 100** koliko je siguran u svoju preporuku.

| Povjerenje | Što znači | Što AI radi |
|------------|-----------|-------------|
| **90-100%** | Vrlo siguran | Predlaže veći ulog (do 3% kapitala) |
| **70-89%** | Siguran | Predlaže srednji ulog (do 2% kapitala) |
| **50-69%** | Nesiguran | Predlaže mali ulog (do 1% kapitala) |
| **< 50%** | Nije siguran | **NE PREDLAŽE TRADE** |

### Zašto postoje ograničenja?

Čak i kad je AI 100% siguran, može pogriješiti. Zato:
- **Nikad ne riskira više od 3%** vašeg novca po jednom tradeu
- I ako deset puta zaredom pogriješi, još uvijek imate 70%+ kapitala

---

## Upravljanje Rizikom (Risk Management)

### Zašto je ovo najvažnije?

Zamislite da imate 10.000 EUR. Ako riskirate 50% po tradeu:
- Prvi gubitak: ostaje 5.000 EUR
- Drugi gubitak: ostaje 2.500 EUR
- **Dva loša tradea i izgubili ste 75% novca!**

Ali ako riskirate samo 2% po tradeu:
- Prvi gubitak: ostaje 9.800 EUR
- Drugi gubitak: ostaje 9.604 EUR
- **Čak i 10 loših tradeova = i dalje imate 81% kapitala**

### Pravila koja AI NIKAD ne krši

| Pravilo | Limit | Zašto |
|---------|-------|-------|
| **Max rizik po tradeu** | 3% | Da jedan loš trade ne uništi kapital |
| **Max dnevni gubitak** | 3% | Da se zaustavi ako stvari idu loše |
| **Max tjedni gubitak** | 6% | Vrijeme za analizu što ne valja |
| **Max otvorenih pozicija** | 3 | Da ne bude "sva jaja u jednoj košari" |

**Ova pravila su "ugrađena" u sustav i ne mogu se zaobići.**

### Risk Validation Gate (NOVO - 2026-01-31)

Od najnovije verzije, sustav ima dodatnu sigurnosnu provjeru zvanu **Risk Validation Gate**.

**Što to znači?**

Prije nego što AI može izvršiti bilo koji trade, MORA proći validaciju:

```
┌─────────────────────────────────────────────────────────────┐
│                   RISK VALIDATION GATE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Želite izvršiti trade?                                    │
│              │                                               │
│              ▼                                               │
│   ┌─────────────────────┐                                   │
│   │ Imate li confidence │  NE  → ❌ TRADE ODBIJEN           │
│   │ i risk_amount?      │──────►  "Risk validation required"│
│   └──────────┬──────────┘                                   │
│              │ DA                                            │
│              ▼                                               │
│   ┌─────────────────────┐                                   │
│   │ Prolazi li sve      │  NE  → ❌ TRADE ODBIJEN           │
│   │ 6 risk provjera?    │──────►  "confidence too low" /    │
│   │ • Confidence ≥50%   │        "weekly_drawdown" /        │
│   │ • Risk % u limitu   │        "max positions reached"    │
│   │ • Daily drawdown OK │                                   │
│   │ • Weekly drawdown OK│  ← NOVO!                          │
│   │ • Pozicije < 3      │                                   │
│   │ • Spread OK         │                                   │
│   └──────────┬──────────┘                                   │
│              │ DA                                            │
│              ▼                                               │
│        ✅ TRADE IZVRŠEN                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Zašto je ovo važno?**

| Prije | Sada |
|-------|------|
| Teoretski je bilo moguće zaobići provjere | Nemoguće zaobići - sustav automatski odbija |
| Ovisilo o tome tko poziva funkciju | Svaki trade MORA proći validaciju |
| Rupa u sigurnosti | Sigurnosna rupa zatvorena |

**Za vas kao korisnika** - ništa se ne mijenja! Samo ste još sigurniji da sustav NIKAD neće napraviti rizičan trade bez vaše dozvole i bez prolaska svih provjera.

### Security Fixes (NOVO - Session 11)

Najnovija verzija donosi dodatna sigurnosna poboljšanja:

| Poboljšanje | Što znači za vas |
|-------------|------------------|
| **Weekly drawdown provjera** | Sustav sada PROVJERAVA tjedni gubitak (max 6%) - prije je bio samo dokumentiran |
| **Automatski reset** | Daily i weekly P/L se automatski resetiraju (UTC midnight / ponedjeljak) |
| **Nema globalnog bypassa** | Više nije moguće zaobići provjere iz koda |
| **Stroga provjera equity** | Trade se odbija ako sustav ne može dohvatiti stanje računa |

**6 provjera koje svaki trade mora proći:**

```
┌─────────────────────────────────────────────────────────────┐
│                    6 RISK PROVJERA                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   1. Confidence         ≥ 50%        ✓ ili ✗               │
│   2. Risk per trade     ≤ tier limit  ✓ ili ✗               │
│   3. Daily drawdown     < 3%         ✓ ili ✗               │
│   4. Weekly drawdown    < 6%         ✓ ili ✗  ← NOVO!      │
│   5. Open positions     < 3          ✓ ili ✗               │
│   6. Spread             < 3 pips     ✓ ili ✗               │
│                                                              │
│   Sve moraju biti ✓ da bi trade prošao!                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Kako se koristi AI Trader?

### Način 1: Terminal (CLI)

Ovo je tekstualno sučelje - tipkate naredbe i dobivate odgovore.

```
┌────────────────────────────────────────────────┐
│  AI Trader>                                     │
│                                                 │
│  Dostupne naredbe:                             │
│  ─────────────────                             │
│  help        → Pokaži pomoć                    │
│  account     → Stanje računa                   │
│  price VALUTA → Trenutna cijena                │
│  analyze VALUTA → AI analiza                   │
│  trade       → Pokreni trade workflow          │
│  positions   → Otvorene pozicije               │
│  emergency   → HITNO zatvori sve               │
│  exit        → Izlaz                           │
└────────────────────────────────────────────────┘
```

### Način 2: Web Dashboard

Ovo je grafičko sučelje u web pregledniku - jednostavnije za korištenje.

| Stranica | Što možete raditi |
|----------|-------------------|
| **Dashboard** | Pregled stanja računa, dnevni profit/gubitak |
| **Chat** | Razgovor s AI-jem, traženje analiza |
| **Analysis** | Detaljna tehnička analiza s grafikonima |
| **Positions** | Upravljanje otvorenim pozicijama |
| **History** | Pregled prošlih tradeova |
| **Settings** | Konfiguracija sustava |
| **Skills** | Uređivanje AI ponašanja |
| **Backtest** | Testiranje strategija na povijesnim podacima |

---

## Primjer korištenja

### Scenarij: Želite vidjeti treba li uložiti u EUR/USD

**Korak 1:** Tražite analizu
```
AI Trader> analyze EUR/USD
```

**Korak 2:** AI prikazuje rezultat
```
═══════════════════════════════════════════════
          ANALIZA: EUR/USD
═══════════════════════════════════════════════

Trenutna cijena: 1.0845

TEHNIČKA ANALIZA:
  • Trend: UZLAZNI (cijena iznad prosjeka)
  • RSI: 58 (neutralno - ni prekupljeno ni preprodano)
  • Podrška: 1.0800
  • Otpor: 1.0900

ARGUMENTI ZA KUPNJU:
  • Cijena je u rastućem trendu
  • RSI pokazuje prostor za rast
  • Američki dolar slabi zbog ekonomskih vijesti

ARGUMENTI PROTIV KUPNJE:
  • Blizu snažnog otpora na 1.0900
  • Sutra izlaze važni ekonomski podaci

POVJERENJE: 72%
PREPORUKA: KUPNJA s oprezom
RIZIK: 2% (srednji tier)

═══════════════════════════════════════════════
Želite li tradati? (da/ne):
```

**Korak 3:** Vi odlučujete

Ako upišete "da", AI izvršava trade. Ako "ne", ništa se ne događa.

---

## Backtesting - Testiranje bez rizika

### Što je backtesting?

Zamislite da možete putovati u prošlost i testirati bi li vaša strategija radila. To je backtesting - **simulacija tradinga na povijesnim podacima**.

### Zašto je korisno?

| Prednost | Objašnjenje |
|----------|-------------|
| **Bez rizika** | Koristite lažni novac na stvarnim podacima |
| **Brzo** | Testirate mjesece tradinga u minutama |
| **Objektivno** | Vidite stvarne rezultate, ne pretpostavke |
| **Učenje** | Razumijete kako strategija radi |

### Primjer rezultata backtesta

```
╔════════════════════════════════════════════╗
║         REZULTATI BACKTESTA                ║
╠════════════════════════════════════════════╣
║  Period: Siječanj - Prosinac 2025          ║
║  Početni kapital: 10.000 EUR               ║
║  Završni kapital: 11.847 EUR               ║
║  ─────────────────────────────────────     ║
║  Ukupni povrat: +18.47%                    ║
║  Max gubitak (drawdown): -4.2%             ║
║  Pobjednički tradeovi: 62%                 ║
║  Ukupno tradeova: 127                      ║
║  ─────────────────────────────────────     ║
║  Sharpe Ratio: 1.45 (dobar)                ║
╚════════════════════════════════════════════╝
```

**Važno:** Prošli rezultati NE garantiraju buduće rezultate!

---

## Tehnička pozadina (pojednostavljeno)

### Komponente sustava

```
┌─────────────────────────────────────────────────────────┐
│                     AI TRADER SUSTAV                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │   MetaTrader │    │   Claude AI  │    │    Vi     │  │
│  │      5       │◄──►│   (mozak)    │◄──►│ (šef)     │  │
│  │   (broker)   │    │              │    │           │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
│         │                   │                   │        │
│         ▼                   ▼                   ▼        │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │ Cijene valuta│    │   Analiza    │    │ Odobrenje │  │
│  │ Izvršenje    │    │   Preporuke  │    │ Odluka    │  │
│  │ tradeova     │    │   Rizik      │    │           │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Što je MetaTrader 5?

**MetaTrader 5 (MT5)** je profesionalni program za trading koji koriste milijuni tradera diljem svijeta. Naš AI Trader koristi MT5 kao "vezu" s burzom.

Zamislite MT5 kao **bankomata** - AI Trader mu daje upute što napraviti (kupi, prodaj), a MT5 to izvršava.

### Što je Claude AI?

**Claude** je umjetna inteligencija koju je napravila tvrtka Anthropic. To je "mozak" našeg sustava koji:
- Čita i razumije podatke s tržišta
- Analizira trendove i pokazatelje
- Generira preporuke
- Komunicira s vama na razumljiv način

---

## Kako "programirati" AI - Postavke sustava

Jedna od najmoćnijih značajki AI Tradera je mogućnost **prilagodbe načina na koji AI razmišlja i donosi odluke**. To nije programiranje u klasičnom smislu - ne trebate znati pisati kod. Umjesto toga, pišete upute na običnom jeziku.

Zamislite da imate novog zaposlenika koji je genij, ali ne zna ništa o vašem poslu. Morate mu objasniti:
1. **Tko je on** i kako se treba ponašati (System Prompt)
2. **Koje vještine** treba koristiti (Skills)
3. **Što treba znati** o tržištu (Knowledge)

### Tri vrste postavki

```
┌─────────────────────────────────────────────────────────────┐
│                 KAKO AI TRADER "MISLI"                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────┐                                       │
│   │  SYSTEM PROMPT  │ ← "Tko sam ja? Kako se ponašam?"      │
│   │    (Osobnost)   │   Definira karakter i pravila AI-ja   │
│   └────────┬────────┘                                       │
│            │                                                 │
│            ▼                                                 │
│   ┌─────────────────┐                                       │
│   │     SKILLS      │ ← "Kako radim specifične zadatke?"    │
│   │   (Vještine)    │   Strategije tradinga (scalping,      │
│   │                 │   swing trading, news trading...)     │
│   └────────┬────────┘                                       │
│            │                                                 │
│            ▼                                                 │
│   ┌─────────────────┐                                       │
│   │   KNOWLEDGE     │ ← "Što znam o svijetu?"               │
│   │    (Znanje)     │   Forex osnove, pravila, lekcije      │
│   │                 │   iz prošlih grešaka                  │
│   └─────────────────┘                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. System Prompt - Osobnost AI-ja

### Što je System Prompt?

**System Prompt** je kao "osobna iskaznica" AI-ja. U njemu definirate:
- Tko je AI (ime, uloga)
- Kako se ponaša (profesionalno, oprezno, prijateljski...)
- Koja pravila MORA poštivati
- Što NIKAD ne smije raditi

### Analogija

Zamislite da zapošljavate osobnog asistenta. Na prvom radnom danu biste mu rekli:

> "Ti si moj financijski savjetnik. Tvoj posao je analizirati tržište i davati mi preporuke. Budi profesionalan i oprezan - radije preskoči priliku nego me uvuci u rizičan posao. Uvijek mi objasni ZAŠTO nešto preporučuješ. I najvažnije - NIKAD ne riskiraj više od 3% mog novca odjednom."

To je System Prompt - samo napisan za AI.

### Kako izgleda System Prompt?

```
┌─────────────────────────────────────────────────────────────┐
│                     SYSTEM PROMPT                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ## Identitet                                                │
│  Ti si AI Trader - profesionalni forex trading asistent.    │
│                                                              │
│  ## Osobnost                                                 │
│  • Profesionalan - fokusiran na činjenice                   │
│  • Oprezan - radije preskoči nego uđi u loš trade           │
│  • Transparentan - uvijek objasni zašto nešto preporučuješ  │
│                                                              │
│  ## Pravila (NEMOGUĆE ZAOBIĆI)                              │
│  • Max rizik 90-100% confidence: 3%                         │
│  • Max rizik 70-89% confidence: 2%                          │
│  • Max rizik 50-69% confidence: 1%                          │
│  • Ispod 50% confidence: NE TRADAJ                          │
│                                                              │
│  ## Što NE raditi                                            │
│  • NE preporučuj trade ako nisi siguran                     │
│  • NE ignoriraj argumente PROTIV tradea                     │
│  • NE tradaj prije velikih vijesti (NFP, ECB, FOMC)        │
│  • NE tradaj petkom navečer                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Kako promijeniti System Prompt?

**Opcija 1: Kroz Web Dashboard**
1. Otvorite Web Dashboard
2. Idite na stranicu **Skills**
3. Kliknite na tab **System Prompt**
4. Uredite tekst
5. Kliknite **Save**

**Opcija 2: Direktno uređivanje datoteke**
1. Otvorite mapu: `Dev/settings/`
2. Otvorite datoteku: `system_prompt.md`
3. Uredite tekst u bilo kojem tekstualnom editoru
4. Spremite

### Primjeri prilagodbe

| Što želite | Što dodati u System Prompt |
|------------|----------------------------|
| AI da bude konzervativniji | "Budi ekstremno oprezan. Preporuči trade samo ako si barem 80% siguran." |
| AI da objašnjava više | "Svaku preporuku objasni detaljno, kao da objašnjavaš početniku." |
| Fokus na određene valute | "Fokusiraj se samo na EUR/USD i GBP/USD. Ignoriraj ostale parove." |
| Izbjegavanje određenih situacija | "Nikad ne tradaj ponedjeljkom ujutro niti petkom popodne." |

---

## 2. Skills - Vještine i strategije

### Što su Skills?

**Skills** su specifične strategije i tehnike koje AI koristi za trading. Svaki skill je kao "recept" za određenu vrstu tradea.

### Analogija

Zamislite kuhara. Kuhar zna puno recepata:
- Recept za pizzu (brzo, jednostavno)
- Recept za gulaš (sporo, kompleksno)
- Recept za salatu (zdravo, lagano)

Svaki recept ima:
- Kada ga koristiti (za ručak, večeru, dijetu...)
- Koje sastojke treba
- Korake pripreme
- Koliko dugo traje

**Skills su "recepti" za trading.**

### Primjer: Scalping Skill

```
┌─────────────────────────────────────────────────────────────┐
│                   SKILL: SCALPING                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ## Što je ovo?                                              │
│  Strategija za brze, kratke tradeove (minutu do sat)        │
│                                                              │
│  ## Kada koristiti                                           │
│  • Za brzu zaradu malih iznosa                              │
│  • Kad je tržište aktivno (London/NY sesija)                │
│  • Kad želiš biti u i van brzo                              │
│                                                              │
│  ## Pravila ulaska                                           │
│  1. Trend na H1 mora biti jasan                             │
│  2. Čekaj pullback na M5 grafikonu                          │
│  3. Ulazi kad cijena odskoči od podrške/otpora              │
│                                                              │
│  ## Pravila izlaska                                          │
│  • Stop Loss: Max 15 pipsa                                  │
│  • Take Profit: 10-20 pipsa                                 │
│  • Max trajanje: 1-2 sata                                   │
│                                                              │
│  ## IZBJEGAVAJ                                               │
│  • Prvih 30 min nakon otvaranja sesije                      │
│  • Vrijeme velikih vijesti                                  │
│  • Kad je spread veći od 1.5 pipsa                          │
│                                                              │
│  ## Posebna pravila rizika                                   │
│  • Max 1% po scalp tradeu                                   │
│  • Max 5 scalp tradeova dnevno                              │
│  • Stani nakon 2 uzastopna gubitka                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Primjer: Swing Trading Skill

```
┌─────────────────────────────────────────────────────────────┐
│                SKILL: SWING TRADING                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ## Što je ovo?                                              │
│  Strategija za višednevne pozicije (2-10 dana)              │
│                                                              │
│  ## Kada koristiti                                           │
│  • Za veće pokrete na tržištu                               │
│  • Kad imaš strpljenja čekati                               │
│  • Kad je jasan dugoročni trend                             │
│                                                              │
│  ## Pravila ulaska                                           │
│  1. Identificiraj glavni trend na dnevnom grafikonu        │
│  2. Čekaj povlačenje cijene do ključne razine               │
│  3. Ulazi kad se potvrdi odbijanje od te razine            │
│                                                              │
│  ## Pravila izlaska                                          │
│  • Stop Loss: Ispod/iznad swing točke (50-100 pipsa)        │
│  • Take Profit: Sljedeća velika razina podrške/otpora       │
│  • Pomakni stop na break-even nakon +50 pipsa              │
│                                                              │
│  ## Posebna pravila rizika                                   │
│  • Max 2 swing pozicije istovremeno                         │
│  • Izbjegavaj držanje preko vikenda ako profit < 30 pipsa  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Kako aktivirati Skill?

Jednostavno - recite AI-ju što želite:

| Što kažete | Koji Skill se aktivira |
|------------|------------------------|
| "scalping analiza EUR/USD" | Scalping |
| "kratkoročni trade" | Scalping |
| "swing analiza GBP/USD" | Swing Trading |
| "višednevni trade" | Swing Trading |
| "analiza prije vijesti" | News Trading |

### Kako napraviti novi Skill?

**Opcija 1: Kroz Web Dashboard**
1. Otvorite Web Dashboard → **Skills** stranica
2. Kliknite na tab **Trading Skills**
3. U lijevom stupcu upišite ime novog skilla (npr. "breakout")
4. Kliknite **Create Skill**
5. Uredite predložak koji se pojavi
6. Kliknite **Save**

**Opcija 2: Direktno kreiranje datoteke**
1. Idite u mapu: `Dev/settings/skills/`
2. Napravite novu datoteku: `ime_skilla.md`
3. Napišite pravila (pogledajte postojeće kao primjer)
4. Spremite

### Struktura dobrog Skilla

Svaki skill treba imati:

| Sekcija | Što sadrži | Primjer |
|---------|------------|---------|
| **Naziv** | Ime strategije | "Breakout Trading" |
| **Opis** | Kratko objašnjenje | "Strategija za trgovanje proboja razina" |
| **Kada koristiti** | Uvjeti aktivacije | "Kad cijena probije važnu razinu" |
| **Pravila ulaska** | Kako ući u trade | "1. Čekaj zatvaranje svijeće iznad otpora" |
| **Pravila izlaska** | Kako izaći iz tradea | "Stop Loss: 20 pipsa, Take Profit: 40 pipsa" |
| **Izbjegavaj** | Kad NE koristiti | "Ne koristi tijekom niskog volumena" |
| **Rizik** | Posebna pravila | "Max 1.5% po breakout tradeu" |

---

## 3. Knowledge - Baza znanja

### Što je Knowledge?

**Knowledge** je sve što AI treba "znati" da bi radio svoj posao. To uključuje:
- Osnove forex tradinga
- Vaša osobna pravila
- Lekcije iz prošlih grešaka

### Analogija

Zamislite da imate bilježnicu u koju zapisujete sve što ste naučili o tradingu. Svaki put kad nešto novo saznate ili napravite grešku, zapišete to u bilježnicu. Sljedeći put kad ste u sličnoj situaciji, pogledate u bilježnicu i sjetite se.

**Knowledge je ta bilježnica - ali AI je čita umjesto vas.**

### Vrste Knowledge datoteka

| Datoteka | Što sadrži | Zašto je korisno |
|----------|------------|------------------|
| **forex_basics.md** | Osnove forex tržišta | AI razumije kontekst |
| **risk_rules.md** | Vaša osobna pravila rizika | AI vas podsjeća na pravila |
| **lessons.md** | Lekcije iz prošlih grešaka | AI ne ponavlja iste greške |

### Primjer: Lekcije iz grešaka

Ovo je **najvažnija** knowledge datoteka. Svaki put kad napravite grešku, zapišite je:

```
┌─────────────────────────────────────────────────────────────┐
│                    NAUČENE LEKCIJE                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ### 15.01.2026 - Gubitak prije ECB-a                       │
│                                                              │
│  **Trade:** EUR/USD LONG @ 1.0850                           │
│  **Gubitak:** -200 EUR (-2%)                                │
│                                                              │
│  **Što se dogodilo:**                                        │
│  Ušao sam u LONG poziciju 2 sata prije ECB odluke           │
│  o kamatnim stopama. Ignorirao sam upozorenje da se         │
│  ne treba tradati prije velikih vijesti. ECB je             │
│  iznenađujuće podigao stope i EUR je pao 80 pipsa.          │
│                                                              │
│  **Lekcija:**                                                │
│  Nikad ne ulaziti u EUR pozicije unutar 4 sata od           │
│  ECB odluke. Vijesti mogu potpuno preokrenuti tržište.      │
│                                                              │
│  **Novo pravilo:**                                           │
│  🚫 Ne tradaj EUR 4h prije/nakon ECB                        │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  ### 20.01.2026 - Revenge trading                           │
│                                                              │
│  **Trade:** GBP/USD SHORT @ 1.2700                          │
│  **Gubitak:** -150 EUR (-1.5%)                              │
│                                                              │
│  **Što se dogodilo:**                                        │
│  Nakon prvog gubitka od -100 EUR, htio sam "nadoknaditi"    │
│  i ušao u trade bez pravilne analize. Rezultat: još         │
│  jedan gubitak.                                             │
│                                                              │
│  **Lekcija:**                                                │
│  Revenge trading je najskuplji oblik tradinga.              │
│  Nakon gubitka - PAUZA, ne novi trade.                      │
│                                                              │
│  **Novo pravilo:**                                           │
│  🚫 Nakon gubitka većeg od 1%, pauza min 2 sata             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Kako AI koristi Knowledge?

Kad analizirate trade, AI automatski:

1. **Provjerava lekcije** - "Jesam li u sličnoj situaciji već griješio?"
2. **Primjenjuje pravila** - "Koja moja pravila vrijede za ovaj trade?"
3. **Upozorava vas** - "PAŽNJA: Slična situacija kao 15.01. - prije ECB-a"

### Kako dodati novi Knowledge?

**Opcija 1: Kroz Web Dashboard**
1. Otvorite Web Dashboard → **Skills** stranica
2. Kliknite na tab **Knowledge Base**
3. Za novu datoteku: upišite ime i kliknite **Create File**
4. Za uređivanje postojeće: kliknite na nju u lijevom stupcu
5. Uredite i kliknite **Save**

**Opcija 2: Direktno uređivanje**
1. Idite u mapu: `Dev/settings/knowledge/`
2. Otvorite ili napravite `.md` datoteku
3. Uredite i spremite

---

## 5. Automatsko Učenje iz Grešaka (NOVO)

### Što je automatsko učenje?

AI Trader sada **automatski uči iz grešaka**. Kada zatvorite trade s gubitkom, sustav:

1. **Analizira** zašto je trade propao
2. **Kategorizira** grešku (8 kategorija)
3. **Zapisuje** u bazu podataka za buduće analize
4. **Generira lekciju** u `lessons.md` ako je gubitak značajan

### Kako to radi?

```
┌─────────────────────────────────────────────────────────────┐
│              AUTOMATSKO UČENJE IZ GREŠAKA                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   [Trade se zatvori s gubitkom]                             │
│              │                                               │
│              ▼                                               │
│   ┌─────────────────────┐                                   │
│   │  Error Analyzer     │ ← Analizira zašto je propalo      │
│   │  (Kategorija)       │                                   │
│   └──────────┬──────────┘                                   │
│              │                                               │
│        ┌─────┴─────┐                                        │
│        │           │                                         │
│        ▼           ▼                                         │
│   ┌─────────┐  ┌───────────┐                                │
│   │ RAG DB  │  │ Lekcija   │ ← Automatski generira          │
│   │ (errors)│  │ lessons.md│   ako gubitak > 1%            │
│   └─────────┘  └───────────┘                                │
│        │                                                     │
│        ▼                                                     │
│   [Sljedeći put kad analizirate istu valutu]               │
│   AI će upozoriti: "PAŽNJA: Slična situacija kao prije!"   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Kategorije grešaka

Sustav automatski prepoznaje 8 vrsta grešaka:

| Kategorija | Što znači | Primjer |
|------------|-----------|---------|
| **OVERCONFIDENT** | Previše samopouzdanja | AI bio 85% siguran, ali trade izgubio |
| **NEWS_IGNORED** | Ignorirane vijesti | Veliki price spike zbog NFP podataka |
| **TECHNICAL_FAILURE** | Tehnička analiza nije radila | Setup je izgledao dobro, ali nije upalio |
| **SENTIMENT_MISMATCH** | Sentiment krivo procijenjen | Mislili smo bullish, ali tržište bearish |
| **TIMING_WRONG** | Loš tajming | Prerano ušli, cijena otišla protiv nas |
| **ADVERSARIAL_IGNORED** | Ignorirana upozorenja | Bear case bio jak, ali smo ga ignorirali |
| **VOLATILITY_SPIKE** | Visoka volatilnost | SL udaren zbog iznenadnog pokreta |
| **UNKNOWN** | Nepoznato | Razlog nije jasan, potrebna analiza |

### Kada se automatski dodaje lekcija?

Sustav automatski dodaje lekciju u `lessons.md` ako:

- **Gubitak > 1% računa** - Značajan gubitak zaslužuje dokumentaciju
- **Ista greška 2+ puta u 7 dana** - Ponavlja se ista pogreška
- **Confidence > 70% ali trade izgubio** - AI bio siguran, ali pogriješio

### Primjer automatski generirane lekcije

```
┌─────────────────────────────────────────────────────────────┐
│  ### [2026-01-31] Technical Setup Failure na EUR_USD        │
│                                                              │
│  **Trade:** EUR_USD LONG @ 1.0850                           │
│  **Gubitak:** -$250.00 (-0.5%)                              │
│  **Kategorija:** TECHNICAL_FAILURE                          │
│                                                              │
│  **Što se dogodilo:**                                        │
│  Tehnički score je bio 68%, ali setup nije radio.           │
│                                                              │
│  **Lekcija:**                                                │
│  Tehnički indikatori sami po sebi nisu dovoljni.            │
│                                                              │
│  **Pravilo:**                                                │
│  Kombiniraj tehnike s fundamentalnom analizom.              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Kako AI koristi naučene lekcije?

Kada analizirate novu priliku, AI automatski:

1. **Provjerava RAG bazu** - "Ima li sličnih grešaka u prošlosti?"
2. **Primjenjuje penalty** - Svaka slična greška smanjuje confidence za 10%
3. **Upozorava vas** - Prikazuje upozorenje s prošlim greškama

**Primjer:**
```
⚠️ UPOZORENJE: Pronađene 2 slične greške za EUR_USD LONG:
   • TECHNICAL_FAILURE: Tehnički indikatori nisu dovoljni sami po sebi.
   • NEWS_IGNORED: Provjeri ekonomski kalendar prije tradea.

Confidence penalty: -20%
```

### Zašto je ovo važno?

| Bez automatskog učenja | S automatskim učenjem |
|------------------------|----------------------|
| Ponavljate iste greške | Sustav vas upozorava |
| Zaboravljate lekcije | Sve je zapisano |
| Ručno vodite dnevnik | Automatski se generira |
| AI ne pamti greške | AI uči iz svakog gubitka |

---

## 6. Konfiguracija - Tehnički parametri

### Što je config.json?

**config.json** je datoteka s tehničkim postavkama sustava. Za razliku od System Prompta koji je na običnom jeziku, ovo su precizni parametri.

### Što možete podesiti?

| Parametar | Što radi | Zadana vrijednost |
|-----------|----------|-------------------|
| `language` | Jezik sučelja | "hr" (hrvatski) |
| `theme` | Tema boja | "dark" (tamna) |
| `confirm_trades` | Traži potvrdu prije tradea | true (da) |
| `temperature` | Koliko je AI "kreativan" | 0.3 (konzervativno) |
| `use_adversarial` | Koristi "za i protiv" analizu | true (da) |
| `default_timeframe` | Zadani vremenski okvir | "H4" (4-satni) |
| `min_rr_ratio` | Minimalni omjer rizik/nagrada | 1.5 |

### Gdje se nalazi?

Datoteka: `Dev/settings/config.json`

### Primjer config.json

```
┌─────────────────────────────────────────────────────────────┐
│                     CONFIG.JSON                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  {                                                           │
│    "interface": {                                            │
│      "name": "AI Trader",                                   │
│      "language": "hr",        ← Hrvatski jezik              │
│      "theme": "dark",          ← Tamna tema                 │
│      "confirm_trades": true    ← Traži potvrdu              │
│    },                                                        │
│                                                              │
│    "ai": {                                                   │
│      "temperature": 0.3,       ← Konzervativni AI           │
│      "use_adversarial": true,  ← Za i protiv analiza        │
│      "use_sentiment": true     ← Analiza sentimenta         │
│    },                                                        │
│                                                              │
│    "analysis": {                                             │
│      "default_timeframe": "H4", ← 4-satni grafikon          │
│      "min_rr_ratio": 1.5        ← Min omjer rizik/nagrada   │
│    }                                                         │
│  }                                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Kako promijeniti?

1. Otvorite datoteku u tekstualnom editoru
2. Promijenite željenu vrijednost
3. Spremite
4. Ponovno pokrenite AI Trader

**Pažnja:** Budite oprezni s uređivanjem - krivi format može srušiti sustav!

---

## Sažetak: Gdje što urediti?

| Želite promijeniti... | Gdje urediti | Tip promjene |
|----------------------|--------------|--------------|
| Kako se AI ponaša | System Prompt | Tekst |
| Trading strategije | Skills | Tekst |
| Što AI zna | Knowledge | Tekst |
| Tehničke parametre | config.json | Brojevi/true/false |

### Preporučeni redoslijed prilagodbe

1. **Prvo:** Dodajte svoje lekcije u `lessons.md`
2. **Drugo:** Prilagodite `risk_rules.md` svojim preferencijama
3. **Treće:** Ako želite novu strategiju, napravite novi Skill
4. **Naposljetku:** Fine-tune System Prompt ako treba

---

## Kako Web Dashboard olakšava uređivanje

Umjesto ručnog uređivanja datoteka, Web Dashboard nudi grafičko sučelje.

### Skills stranica

```
┌─────────────────────────────────────────────────────────────┐
│  📚 Skills & Knowledge Editor                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [System Prompt] [Trading Skills] [Knowledge Base]  ← Tabovi │
│                                                              │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │              │  │                                      │ │
│  │  📄 scalping │  │  # Scalping                         │ │
│  │  📄 swing    │  │                                      │ │
│  │  📄 news     │  │  ## Kada aktivirati                 │ │
│  │              │  │  - "scalping analiza"               │ │
│  │ ─────────── │  │  - "kratkoročni trade"              │ │
│  │              │  │                                      │ │
│  │ Add New:     │  │  ## Entry pravila                   │ │
│  │ [breakout  ] │  │  1. Trend na H1 jasan              │ │
│  │ [Create]     │  │  2. Čekaj pullback na M5           │ │
│  │              │  │  ...                                │ │
│  │              │  │                                      │ │
│  │              │  │  [Save] [Delete]                    │ │
│  │              │  │                                      │ │
│  └──────────────┘  └──────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Prednosti Web Dashboarda

| Značajka | Korist |
|----------|--------|
| **Preview** | Vidite kako će tekst izgledati |
| **Validacija** | Upozorava na greške |
| **Jedan klik** | Save/Delete bez traženja datoteka |
| **Backup** | Možete resetirati na original |

---

## Praktični primjer: Kreiranje novog Skilla

Zamislimo da želite napraviti strategiju za **trading na proboju** (breakout).

### Korak 1: Otvorite Skills Editor

1. Pokrenite Web Dashboard (`streamlit run dashboard.py`)
2. Idite na stranicu **Skills**
3. Kliknite tab **Trading Skills**

### Korak 2: Kreirajte novi Skill

1. U lijevom stupcu, upišite: `breakout`
2. Kliknite **Create Skill**

### Korak 3: Ispunite predložak

```markdown
# Breakout Trading

## Opis
Strategija za trgovanje kada cijena probije važnu razinu
podrške ili otpora.

## Kada koristiti
- Kad cijena dotakne istu razinu 2-3 puta bez proboja
- Kad se volumen povećava blizu razine
- Najbolje tijekom London ili NY sesije

## Entry pravila
1. Identificiraj jaku razinu podrške/otpora (min 2 dodira)
2. Čekaj zatvaranje svijeće IZNAD otpora (za long)
   ili ISPOD podrške (za short)
3. Potvrda: povećan volumen na proboju
4. Ulaz: na retracementu prema razini (sada postaje podrška/otpor)

## Exit pravila
- Stop Loss: Ispod razine proboja + spread (15-25 pipsa)
- Take Profit: Sljedeća značajna razina (min 1.5x SL)
- Trail stop nakon +30 pipsa

## IZBJEGAVAJ
- Proboje tijekom niskog volumena (azijska sesija)
- Lažne proboje (bez volumena, brzo se vraća)
- Proboje prije velikih vijesti

## Risk Management
- Max 2% po breakout tradeu
- Max 2 breakout tradea dnevno
- Ne ulazi ako je R:R manji od 1.5:1
```

### Korak 4: Spremite

Kliknite **Save** - novi skill je spreman za korištenje!

### Korak 5: Testirajte

U Chat-u upišite: "breakout analiza EUR/USD"

AI će sada koristiti vaš novi skill za analizu!

---

## Kako pokrenuti sustav

### Preduvjeti

1. **MetaTrader 5** - mora biti instaliran i ulogiran
2. **Python** - programski jezik (već instaliran)
3. **Demo račun** - s virtualnim novcem za vježbanje

### Pokretanje

**Za Terminal (CLI):**
```
1. Otvorite MetaTrader 5 i pričekajte da se učita
2. Otvorite terminal (Command Prompt)
3. Upišite: cd "C:\Users\mglav\Projects\AI Trader\Dev"
4. Upišite: python trader.py
```

**Za Web Dashboard:**
```
1. Otvorite MetaTrader 5 i pričekajte da se učita
2. Otvorite terminal (Command Prompt)
3. Upišite: cd "C:\Users\mglav\Projects\AI Trader\Dev"
4. Upišite: streamlit run dashboard.py
5. Otvorit će se web preglednik na adresi http://localhost:8501
```

---

## Često postavljana pitanja (FAQ)

### Mogu li izgubiti novac?

**DA.** Trading uvijek nosi rizik gubitka. AI Trader pomaže smanjiti rizik, ali ga ne može eliminirati. Nikad ne ulažite više nego što možete priuštiti izgubiti.

### Je li ovo legalno?

**DA.** Forex trading je legalan. AI Trader je samo alat koji vam pomaže u analizi - vi donosite konačne odluke.

### Koliko mogu zaraditi?

**Nema garancija.** Profesionalni traderi ciljaju 10-30% godišnje. Bilo tko tko obećava veće zarade vjerojatno laže.

### Zašto AI ne tradi sam?

Zato što:
1. **Regulacije** - potpuno autonomno trgovanje ima pravna ograničenja
2. **Sigurnost** - ljudska kontrola sprječava katastrofalne greške
3. **Odgovornost** - vi ste odgovorni za svoje financije

### Što ako AI pogriješi?

Zato postoje:
- **Limiti rizika** - nikad ne gubi više od 3% odjednom
- **Stop-loss** - automatski zatvara gubitničke pozicije
- **Vaše odobrenje** - vi imate zadnju riječ

### Mogu li koristiti pravi novac?

Preporuka je:
1. **Prvo koristite demo račun** s virtualnim novcem
2. **Testirajte barem 2-3 mjeseca**
3. **Tek onda** razmislite o pravom novcu - i to s malim iznosima

---

## Rječnik pojmova

### Forex pojmovi

| Pojam | Objašnjenje |
|-------|-------------|
| **Forex** | Tržište valuta (Foreign Exchange) |
| **Pip** | Najmanja promjena cijene (npr. 0.0001) |
| **Lot** | Jedinica veličine tradea (1 lot = 100.000 jedinica) |
| **Spread** | Razlika između kupovne i prodajne cijene |
| **Long** | Kupnja (očekujete rast) |
| **Short** | Prodaja (očekujete pad) |
| **Stop-Loss** | Automatsko zatvaranje ako cijena padne previše |
| **Take-Profit** | Automatsko zatvaranje kada dosegnete cilj |
| **Drawdown** | Najveći pad vrijednosti portfelja |
| **Equity** | Ukupna vrijednost računa uključujući otvorene pozicije |
| **Margin** | Novac "zaključan" kao jamstvo za trade |
| **Leverage** | "Poluga" - mogućnost tradanja s više novca nego imate |
| **RSI** | Pokazatelj - je li valuta "prekupljena" ili "preprodana" |
| **EMA** | Pomični prosjek - pokazuje trend |
| **Backtesting** | Testiranje strategije na povijesnim podacima |
| **Breakout** | Proboj - kad cijena prođe važnu razinu |
| **Support** | Podrška - razina ispod koje cijena teško pada |
| **Resistance** | Otpor - razina iznad koje cijena teško raste |
| **Scalping** | Strategija brzih, kratkih tradeova |
| **Swing Trading** | Strategija višednevnih pozicija |
| **R:R Ratio** | Omjer rizika i nagrade (npr. 1:2 = riskirate 1 za zaradu 2) |

### AI Trader pojmovi

| Pojam | Objašnjenje |
|-------|-------------|
| **System Prompt** | Upute koje definiraju osobnost i pravila AI-ja |
| **Skill** | Strategija ili vještina koju AI koristi |
| **Knowledge** | Baza znanja koju AI koristi za kontekst |
| **Confidence** | Ocjena sigurnosti AI-ja (0-100%) |
| **Adversarial Thinking** | Analiza "za i protiv" prije odluke |
| **RAG** | Sustav koji provjerava prošle greške |
| **Auto Learning** | Automatsko učenje iz grešaka |
| **Error Analyzer** | Modul koji kategorizira greške |
| **config.json** | Datoteka s tehničkim postavkama |
| **Dashboard** | Web sučelje za upravljanje sustavom |
| **CLI** | Tekstualno sučelje (Command Line Interface) |

---

## Zlatna pravila za početnike

1. **Nikad ne ulažite novac koji vam treba za život**
2. **Počnite s demo računom** - vježbajte bez rizika
3. **Učite, učite, učite** - trading je vještina koja se razvija godinama
4. **Poštujte risk management** - AI Trader to radi automatski
5. **Ne jurite brzu zaradu** - sporo i stabilno pobjeđuje
6. **Prihvatite gubitke** - dio su igre, čak i najbolji gube 40% tradeova
7. **Vodite dnevnik** - zapisujte što radite i učite iz grešaka

---

## Kontakt i podrška

Ovaj sustav je razvijen za internu upotrebu tvrtke **Sirius Grupa d.o.o.**

Za pitanja i podršku, kontaktirajte administratora sustava.

---

*Dokument kreiran: 2026-01-31*
*Zadnje ažuriranje: 2026-01-31*
*Verzija: 2.3 - Security Fixes (weekly drawdown, auto-reset)*

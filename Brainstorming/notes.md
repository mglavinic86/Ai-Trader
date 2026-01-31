# Bilješke i Ideje - MOLTBOT FOREX

---

## [2026-01-30] Inicijalna analiza dokumenta

### Pregled
- Dokument "ideja.md" sadrži detaljan tehnički plan (480+ linija)
- Verzija 1.0, Sirius Grupa d.o.o.
- Fokus: Forex trading s AI asistencijom

### Ključne komponente identificirane:
1. **Moltbot Gateway** - konverzacijsko sučelje
2. **AI Decision Engine** - Claude za analizu
3. **Market Intelligence** - news, calendar, sentiment
4. **Trading Engine** - orders, risk, execution
5. **Broker API** - OANDA primary

### Timeline
- 12 tjedana implementacije
- 5 faza: Foundation → Core → AI → Automation → Optimization
- Cilj: Live trading nakon 3 mjeseca demo testiranja

### Procijenjeni troškovi
- Mjesečno: 70-190 EUR
- Development: 120-160 sati

### Sigurnosne napomene
- Moltbot izvršava komande - NE pokretati na glavnom računalu
- Dedicated OANDA sub-account za bota
- API keys u Vault, ne u kodu
- Prompt injection zaštita kritična

---

## Otvorena pitanja

1. **Moltbot licenciranje?** - Provjeriti uvjete korištenja
2. **OANDA EU vs US account?** - ESMA leverage limiti (30:1)
3. **VPN za VPS pristup?** - Koji provider?
4. **Backup strategija?** - S3 vs lokalno?
5. **Multi-user u budućnosti?** - Arhitektura podržava?

---

## Ideje za poboljšanje

- [ ] Integracija s TradingView alertima
- [ ] Webhook za externe signale
- [ ] Mobile push notifications
- [ ] Automated daily/weekly reports
- [ ] Drawdown recovery mode

---

## Reference iz dokumenta

- OANDA Demo: https://www.oanda.com/eu-en/trading/demo-account/
- OANDA API: https://developer.oanda.com/rest-live-v20/introduction/

---
*Dodaj nove sesije iznad ove linije*

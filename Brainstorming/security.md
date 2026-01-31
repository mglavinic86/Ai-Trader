# Sigurnost - AI TRADER (Claude Code)

---

## A) Lokalna sigurnost

| Pravilo | Opis |
|---------|------|
| **API Keys u .env** | Nikad ne commitaj .env - dodaj u .gitignore |
| **Dedicated Account** | Koristi dedicated OANDA sub-account samo za trading |
| **No Keys in Code** | Nikad hardcode API keys u Python skripte |

### .gitignore primjer
```
.env
*.db
data/cache/*
__pycache__/
```

---

## B) OANDA API Security

| Mjera | Implementacija |
|-------|----------------|
| Permissions | API key s ograničenim permissionima (no withdrawal) |
| Demo First | Testiraj na Practice accountu minimalno 3 mjeseca |
| IP Whitelist | Opcionalno - konfiguriraj na OANDA dashboardu |
| Key Rotation | Rotate API keys svakih 90 dana |

---

## C) Risk Management (Hard-Coded)

> Ovi limiti su u kodu i ne mogu biti overrideani!

| Parametar | Vrijednost | Napomena |
|-----------|------------|----------|
| Max risk per trade | 1% equity | Apsolutni limit |
| Max daily drawdown | 3% equity | Pauzira trading |
| Max weekly drawdown | 6% equity | Zahtijeva review |
| Max concurrent positions | 3 | Diversifikacija |
| Max leverage | 10:1 | Konzervativno |

### Implementacija u kodu
```python
# risk_manager.py - HARD LIMITS
MAX_RISK_PER_TRADE = 0.01  # 1%
MAX_DAILY_DRAWDOWN = 0.03  # 3%
MAX_WEEKLY_DRAWDOWN = 0.06  # 6%
MAX_CONCURRENT_POSITIONS = 3
MAX_LEVERAGE = 10

def validate_trade(equity, risk_amount, open_positions):
    """Returns (valid, reason)"""
    if risk_amount > equity * MAX_RISK_PER_TRADE:
        return False, f"Risk exceeds {MAX_RISK_PER_TRADE*100}%"
    if len(open_positions) >= MAX_CONCURRENT_POSITIONS:
        return False, f"Max {MAX_CONCURRENT_POSITIONS} positions"
    return True, "OK"
```

---

## D) Human-in-the-Loop

Svaki trade zahtijeva tvoju potvrdu:

```
Claude: Predlažem long EUR/USD:
- Entry: 1.0843
- SL: 1.0800 (43 pips)
- TP: 1.0920 (77 pips)
- Risk: $43 (0.86% equity)
- R:R = 1.8

Želiš li izvršiti? (da/ne/modificiraj)
```

Ti uvijek imaš zadnju riječ.

---

## E) Backup & Recovery

| Aspekt | Plan |
|--------|------|
| Trade Log | SQLite database (data/trades.db) |
| Daily Export | CSV export za audit trail |
| Git | Commitaj sve osim .env i data/ |
| Cloud Backup | Opcionalno - sync data/ folder |

---

## Checklist prije tradinga

### Setup
- [ ] OANDA demo account kreiran
- [ ] API key s limitiranim permissions
- [ ] .env konfiguriran (ne committan!)
- [ ] Risk limits hard-coded
- [ ] Trade logging radi

### Prije live tradinga
- [ ] 3+ mjeseca demo testiranja
- [ ] Profitabilan na demo
- [ ] Risk management testiran
- [ ] Backup sustav radi
- [ ] Znaš kako brzo zatvoriti sve pozicije

---

## Emergency Procedures

### Ako nešto krene po zlu:
1. **ODMAH:** Zatvori sve pozicije na OANDA web platformi
2. Disable API key na OANDA dashboardu
3. Review trade log
4. Investigate & fix
5. Re-enable nakon fixa

### Brzo zatvaranje svih pozicija:
```python
# emergency_close.py
python scripts/emergency_close.py  # Zatvara SVE pozicije
```

Ili manualno na: https://fxpractice.oanda.com (demo) / https://fxtrade.oanda.com (live)

---

## Što je pojednostavljeno

| Staro (VPS) | Novo (Lokalno) |
|-------------|----------------|
| VPS firewall | Windows firewall (default) |
| Fail2ban | Nepotrebno |
| SSH hardening | Nepotrebno |
| Docker security | Nepotrebno |
| HashiCorp Vault | .env file |
| VPN za admin | Nepotrebno |

Lokalni sustav je inherentno sigurniji jer:
- Nema javno dostupnih endpointa
- Nema network exposure
- Ti kontroliraš fizički pristup

---
*Ažurirano: 2026-01-30 | Claude Code lokalna arhitektura*

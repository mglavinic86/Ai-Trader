# AI TRADER (Claude Code) - Vizija

## Vizija
Automatizirani forex trading sustav koji koristi **Claude Code** kao sučelje i **Claude AI** za analizu tržišta i donošenje odluka. Interni sustav za osobnu upotrebu.

## Problem koji rješavamo
- Manualno praćenje forex tržišta je vremenski zahtjevno (24/5)
- Emotivne odluke u tradingu vode do gubitaka
- Nedostatak discipline u risk managementu
- Propuštanje trading prilika zbog ljudskih ograničenja

## Ciljevi projekta
- Automatizirano praćenje i analiza forex tržišta 24/5
- AI-potpomognuto donošenje trading odluka
- Risk management s hard-coded limitima (ne mogu biti overrideani)
- Human-in-the-loop odobrenje za sve tradeove
- Post-trade analiza i kontinuirano učenje

## Ciljana publika
- Sirius Grupa d.o.o. (interni sustav)
- Samo ti - nije za javnost

## Ključne vrijednosti

| Aspekt | Naš pristup |
|--------|-------------|
| Jednostavnost | Lokalno, bez infrastrukture |
| Sigurnost | Hard-coded risk limiti, human approval |
| Transparentnost | Explainable AI - svaka odluka ima obrazloženje |
| Kontrola | Human-in-the-loop, ne fully autonomous |
| Tehnologija | Claude Code + Python skripte |

## Razlike: Moltbot vs Claude Code

| Aspekt | Moltbot (staro) | Claude Code (novo) |
|--------|-----------------|-------------------|
| Sučelje | Telegram/Discord | Terminal (CLI) |
| Infrastruktura | VPS, Docker | Lokalno računalo |
| Kompleksnost | Visoka | Niska |
| Setup | Tjedni | Sati |
| Troškovi | ~150 EUR/mj | ~80 EUR/mj |
| Human approval | Telegram buttons | Direktno u CLI |

## Zašto Claude Code?
1. **Već ga koristiš** - nema novog alata za učiti
2. **Direktna interakcija** - bez posrednika (Telegram, bot)
3. **Može izvršavati kod** - Python skripte za trading
4. **MCP serveri** - memory, filesystem već konfigurirani
5. **Jednostavnije** - manje pokretnih dijelova

---
*Projekt: Sirius Grupa d.o.o. | Ažurirano: 2026-01-30*

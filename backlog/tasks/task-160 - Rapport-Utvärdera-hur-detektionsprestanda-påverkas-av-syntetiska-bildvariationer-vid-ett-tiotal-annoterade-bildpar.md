---
id: TASK-160
title: >-
  Rapport - Utvärdera hur detektionsprestanda påverkas av syntetiska
  bildvariationer vid ett tiotal manuellt annoterade bildpar
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-18T16:05:00Z'
updated_date: '2026-11-18T18:54:00Z'
labels:
  - report
  - evaluate
dependencies: []
references:
  - docs/beteende.md
priority: medium
type: docs
ordinal: 296000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Utvärdering av hur detektionsprestandan efter modellträning påverkas av syntetiska bildvariationer när datasetet bara innehåller ett tiotal manuellt annoterade bildpar.

### Bakgrund

Appen är byggd för att användaren fångar bildpar, annoterar dem manuellt och tränar en modell på dem. I praktiken hinner en användare bara få ihop ett tiotal annoterade bildpar innan första träningen, och datasetvyn kan då utöka datasetet med syntetiska variationer: rotation, vändning, storlek och färg, i lägena en typ per bild, alla valda variationer eller slumpvisa kombinationer, med 0-20 variationer per bildpar. Ingen vet om utökningen hjälper, vilka typer som hjälper mest eller hur många variationer som är värda att skapa, så i dag gissar användaren på inställningarna i dialogen "Utöka med bildvariationer".

### Det som ska utvärderas

* Ett tiotal manuellt annoterade bildpar utan syntetiska variationer (baslinje).
* Samma bildpar utökade med en variationstyp i taget: rotation, vändning, storlek och färg.
* Samma bildpar utökade med kombinationer av flera variationstyper.
* Antalet variationer per bildpar i ökande steg, för att hitta var kurvan planar ut.

Rapporten ska svara på:

* Vilka bildvariationer som ger bäst förbättring av detektionsprestandan jämfört med enbart de manuellt annoterade bildparen.
* Var den övre gränsen ligger, det vill säga vid vilket antal variationer per bildpar som fler variationer inte längre påverkar prestandan positivt.

### Mall för genomförandet

* Utgå från angiven basmodell.
* Genomför träning (detektion av överträning aktiverat).
* Upprepa med de olika parametrarna/metoderna som ska ingå i utvärderingen.
* Använd funktionalitet som finns i applikationen i första hand.
* Vid behov av annan funktionalitet skapas script/program som sparas separat från övrig applikationslogik.
* Mät resultat för varje kombination som ska testas.
* Utvärdera skillnader och lärdomar från resultaten.
* Modeller som tränats under utvärderingen behöver inte lämnas kvar, de kan tas bort, men ta inte bort data som användaren har skapat manuellt och nu ligger i applikationen.
* Skapa en markdown-rapport med summering, resonemang, tabeller och grafer för att presentera resultatet. En rapport per utvärderingsuppgift.

### Förutsättningar som påverkar jämförbarheten

* Datasetet är litet, så val-delen blir bara ett par bildpar och val-mAP blir brusigt. Körningarna behöver därför mätas mot en fast, manuellt annoterad uppsättning som hålls utanför träningen och aldrig utökas med variationer, annars mäter de olika saker.
* Variationerna dras slumpmässigt: `DatasetStore.add_variations()` tar en seed, men datasetvyn skickar ingen, så samma inställning ger olika bilder mellan körningarna. Det påverkar hur två körningar får jämföras.
* Antalet variationer per bildpar styr bara lägena "Alla valda variationer" och "Slumpvisa kombinationer"; läget "En per variationstyp" ger en bild per aktiv typ och struntar i antalet.
* Träningen kan stoppas av överträningsdetektionen, så antalet epoker skiljer sig mellan körningar och behöver redovisas per körning.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 En baslinje är tränad och utvärderad på enbart de manuellt annoterade bildparen, utan syntetiska variationer.
- [x] #2 Alla körningar använder samma basmodell, epokantal, bildstorlek och batch, och utvärderas mot samma fasta uppsättning manuellt annoterade bildpar som aldrig ingår i träningen och aldrig utökas med variationer.
- [x] #3 Varje variationstyp - rotation, vändning, storlek och färg - är utvärderad var för sig mot baslinjen.
- [x] #4 Minst en kombination av flera variationstyper är utvärderad mot baslinjen och mot de enskilda typerna.
- [x] #5 Antalet variationer per bildpar är varierat i minst fyra steg, till exempel 1, 2, 5, 10 och 20, med samma variationstyp eller kombination.
- [x] #6 Rapporten rangordnar variationstyperna efter förbättring i mAP50-95, mAP50 totalt och per vy när utvärderingskällan har fångstpar, samt falsklarm per bild, med tabeller som underlag.
- [x] #7 Rapporten anger vid vilket antal variationer per bildpar som ytterligare variationer inte längre ger förbättring, eller redovisar varför ingen sådan gräns kunde fastställas inom det testade intervallet.
- [x] #8 Varje körning redovisas med antal bildpar i train och val, antal epoker, om träningen stoppades av överträningsdetektionen och körtid.
- [x] #9 Spridningen mellan upprepade körningar med samma inställningar är redovisad, så en skillnad mellan två inställningar kan skiljas från slumpen.
- [x] #10 Rapporten ligger i en markdown-fil med summering, resonemang, tabeller och grafer, och avslutas med en rekommendation om vilka variationer som är värda att använda vid ett tiotal bildpar.
- [x] #11 Manuellt skapade bilder och annoteringar i applikationen är oförändrade efter utvärderingen; modeller som tränats för utvärderingen får vara borttagna.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
- [x] #6 Utvärdering genomförd enligt instruktion och sparad som en rapport i markdown-fil
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Dela appens dataset med appens egen train_val_split (seed 42, 80 %): 8 bildpar till träning, 2 bildpar som fast utvärderingsuppsättning som aldrig utökas.
2. Bygg en matris: baslinje utan variationer, rotation, vändning, storlek och färg var för sig, alla fyra tillsammans, och kombinationen i 1, 2, 5, 10 och 20 variationer per bildpar. Tre frön per konfiguration, två körningar för baslinjen.
3. Kör varje konfiguration genom appens egna moduler: add_variations, export_yolo, train_task och evaluate_run. Skriptet scripts/variation_eval.py ligger utanför applikationslogiken och rör aldrig användarens dataset.
4. Kör matrisen med överträningsvakten på, som uppgiften säger. Vakten stoppade varje körning innan modellen lärde sig något, så kör en kompletterande matris med vakten avstängd för att kunna jämföra variationstyperna.
5. Skriv markdown-rapporten med summering, resonemang, tabeller och grafer, och avsluta med en rekommendation.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Datasetet har 10 manuellt annoterade bildpar (53 objekt, klassen zipper) och inga syntetiska bilder. Appens egen delning ger 8 bildpar till träning och 2 till den fasta utvärderingsuppsättningen (bild-id 29, 30, 43, 44).

Första matrisen kördes med överträningsvakten på. Vakten stoppade samtliga 29 körningar efter 11-59 epoker, och alla konfigurationer med 0-2 variationer per bildpar landade på mAP50-95 0,002. Orsaken är att 12 träningsbilder med batch 8 bara ger två optimeringssteg per epok, så vaktens tio epoker utan förbättring är tjugo steg - modellen behöver omkring hundra innan valvärdet rör sig.

Därför kördes en kompletterande matris med --overfitting-guard off, så alla körningar går 100 epoker. Den är den som svarar på vilka variationstyper som hjälper, och avvikelsen redovisas i rapporten.

Verifiering:
- AC1-AC5: 29 körningar i matrisen med vakten på och 29 med vakten av, alla med samma basmodell (yolo26m), 100 epoker, imgsz 800 och batch 8. Baslinjen har synthetic_pairs 0; typerna rotation, flip, scale och color körs var för sig; all-1 är kombinationen; antalet varieras i 1, 2, 5, 10 och 20.
- AC2: eval_fixed skapas en gång i prepare ur appens egen train_val_split (bild-id 29, 30, 43, 44) och rörs sedan aldrig. train_base innehåller de övriga 8 paren. Ingen körning ser eval-bilderna.
- AC6: rapporten har en explicit rangordning per matris, tabeller med mAP50-95, mAP50, mAP50-95 per vy och falska detektioner per bild.
- AC7: rapporten redovisar att ingen övre gräns kunde fastställas, eftersom kurvan aldrig når baslinjen inom 1-20 variationer.
- AC8: varje körning står i en tabell med train/val i par och bilder, epoker, om vakten stoppade den och körtid.
- AC9: spridningstabell per konfiguration med antal körningar, medelvärde, standardavvikelse och min-max. Baslinjens två körningar är identiska, vilket visar att träningen är deterministisk.
- AC11: användarens dataset är oförändrat efter körningen: 20 bilder, 0 syntetiska, 53 objekt och samma updated-tidsstämpel. Alla tränade modeller ligger i ~/.xray-detector/eval/, inte i models/trained/.

Tester: uv run pytest -q -p no:xdist gav 971 passed, 1 skipped. Med -n auto faller 3 GUI-tester i test_shortcuts.py på Qt-tajming; de går igenom enskilt och seriellt och rör inte den här ändringen. uv run ruff check . går igenom.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Utvärderingen är genomförd och rapporten ligger i docs/rapporter/bildvariationer.md med grafer i docs/rapporter/bilder/.

Vad som gjordes: appens dataset (10 manuellt annoterade bildpar, 53 objekt) delades med appens egen train_val_split i 8 träningspar och 2 fasta utvärderingspar. scripts/variation_eval.py körde 29 träningar med appens egna moduler (add_variations, export_yolo, train_task, evaluate_run): baslinje, rotation, vändning, storlek och färg var för sig, alla fyra tillsammans, och kombinationen i 1, 2, 5, 10 och 20 variationer per bildpar, tre frön per konfiguration.

Resultat: med överträningsvakten på, som uppgiften säger, stoppade den varje körning efter 11-47 epoker. Tolv träningsbilder med batch 8 ger bara två optimeringssteg per epok, så vaktens tio epoker utan förbättring är tjugo steg - modellen behöver omkring hundra innan valvärdet rör sig. Alla konfigurationer med 0-2 variationer landade därför på mAP50-95 0,002. En kompletterande matris med vakten avstängd (redovisad som avvikelse) visar den verkliga effekten: baslinjen når 0,201, storlek 0,205 och färg 0,202 ligger på samma nivå, medan rotation 0,148, vändning 0,147 och kombinationen 0,137 ligger under. Fler variationer hjälper inte; kurvan når aldrig baslinjen inom 1-20.

Rekommendationen i rapporten: vid ett tiotal bildpar, träna på de annoterade paren som de är och lägg arbetet på fler annoterade bildpar i stället. Per vy höjer alla variationstyper mAP på vy 1 men sänker den på vy 2.

Risker och uppföljning: utvärderingsuppsättningen är fyra bilder och tio objekt, så skillnader under ungefär 0,05 är brus. Styrkorna är dialogens standardvärden, så rapporten säger inget om svagare inställningar. Att vakten stoppar träningen på ett litet dataset är en egen fråga som inte hörde till den här uppgiften.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-161
title: >-
  Rapport - samma utvärdering av syntetiska bildvariationer med RF-DETR large
  dvxray som basmodell
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-18T19:18:00Z'
updated_date: '2026-11-18T19:19:00Z'
labels:
  - report
  - evaluate
dependencies: []
references:
  - docs/rapporter/bildvariationer.md
priority: medium
type: docs
ordinal: 297000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Samma utvärdering som TASK-160, men med **RF-DETR large dvxray** (`models/checkpoint_best_total.pth`) som basmodell i stället för YOLO26 medium. Syftet är att se om slutsatsen om syntetiska bildvariationer håller för den modell användaren faktiskt har tränat på röntgenbilder.

### Bakgrund

TASK-160 visade att överträningsvakten stoppar träningen innan modellen lär sig något på ett tiotal annoterade bildpar, och att ingen variationstyp slår baslinjen när träningen får gå 100 epoker. Den slutsatsen drogs med YOLO26 medium. RF-DETR large dvxray är redan tränad på röntgenbilder, så den kan svara annorlunda på samma variationer.

### Det som ska göras

* Samma matris som TASK-160: baslinje, rotation, vändning, storlek och färg var för sig, alla fyra tillsammans, och kombinationen i 1, 2, 5, 10 och 20 variationer per bildpar.
* Samma fasta utvärderingsuppsättning (bild-id 29, 30, 43, 44) och samma träningsdel (8 bildpar).
* Samma epokantal, bildstorlek och batch som YOLO-körningen, så de två rapporterna går att jämföra.
* RF-DETR-exporten har train/valid/test, så val-delen blir ett bildpar. Det påverkar överträningsvakten och ska redovisas.
* En markdown-rapport med summering, resonemang, tabeller och grafer, som avslutas med en rekommendation.

### Förutsättningar som påverkar jämförbarheten

* RF-DETR large är betydligt tyngre än YOLO26 medium, så antalet körningar och epoker påverkar körtiden.
* RF-DETR:s early stopping är paketets egen mekanism, inte ultralytics.
* Basmodellen har 15 klasser i sitt huvud; träningen byter ut det mot datasetets enda klass.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 En baslinje är tränad och utvärderad på enbart de manuellt annoterade bildparen, utan syntetiska variationer.
- [ ] #2 Alla körningar använder samma basmodell, epokantal, bildstorlek och batch, och utvärderas mot samma fasta uppsättning manuellt annoterade bildpar som aldrig ingår i träningen och aldrig utökas med variationer.
- [ ] #3 Varje variationstyp - rotation, vändning, storlek och färg - är utvärderad var för sig mot baslinjen.
- [ ] #4 Minst en kombination av flera variationstyper är utvärderad mot baslinjen och mot de enskilda typerna.
- [ ] #5 Antalet variationer per bildpar är varierat i minst fyra steg, till exempel 1, 2, 5, 10 och 20, med samma variationstyp eller kombination.
- [ ] #6 Rapporten rangordnar variationstyperna efter förbättring i mAP50-95, mAP50 totalt och per vy när utvärringskällan har fångstpar, samt falsklarm per bild, med tabeller som underlag.
- [ ] #7 Rapporten anger vid vilket antal variationer per bildpar som ytterligare variationer inte längre ger förbättring, eller redovisar varför ingen sådan gräns kunde fastställas inom det testade intervallet.
- [ ] #8 Varje körning redovisas med antal bildpar i train och val, antal epoker, om träningen stoppades av överträningsdetektionen och körtid.
- [ ] #9 Spridningen mellan upprepade körningar med samma inställningar är redovisad, så en skillnad mellan två inställningar kan skiljas från slumpen.
- [ ] #10 Rapporten ligger i en markdown-fil med summering, resonemang, tabeller och grafer, och avslutas med en rekommendation om vilka variationer som är värda att använda vid ett tiotal bildpar.
- [ ] #11 Manuellt skapade bilder och annoteringar i applikationen är oförändrade efter utvärderingen; modeller som tränats för utvärderingen får vara borttagna.
- [ ] #12 Rapporten jämför resultatet med TASK-160:s YOLO-körning och säger om slutsatsen håller för RF-DETR large dvxray.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

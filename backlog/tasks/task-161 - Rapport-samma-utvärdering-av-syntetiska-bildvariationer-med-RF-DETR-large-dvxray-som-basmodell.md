---
id: TASK-161
title: >-
  Rapport - samma utvärdering av syntetiska bildvariationer med RF-DETR large
  dvxray som basmodell
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-18T19:18:00Z'
updated_date: '2026-11-18T20:35:00Z'
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
- [x] #1 En baslinje är tränad och utvärderad på enbart de manuellt annoterade bildparen, utan syntetiska variationer.
- [x] #2 Alla körningar använder samma basmodell, epokantal, bildstorlek och batch, och utvärderas mot samma fasta uppsättning manuellt annoterade bildpar som aldrig ingår i träningen och aldrig utökas med variationer.
- [x] #3 Varje variationstyp - rotation, vändning, storlek och färg - är utvärderad var för sig mot baslinjen.
- [x] #4 Minst en kombination av flera variationstyper är utvärderad mot baslinjen och mot de enskilda typerna.
- [x] #5 Antalet variationer per bildpar är varierat i minst fyra steg, till exempel 1, 2, 5, 10 och 20, med samma variationstyp eller kombination.
- [x] #6 Rapporten rangordnar variationstyperna efter förbättring i mAP50-95, mAP50 totalt och per vy när utvärringskällan har fångstpar, samt falsklarm per bild, med tabeller som underlag.
- [x] #7 Rapporten anger vid vilket antal variationer per bildpar som ytterligare variationer inte längre ger förbättring, eller redovisar varför ingen sådan gräns kunde fastställas inom det testade intervallet.
- [x] #8 Varje körning redovisas med antal bildpar i train och val, antal epoker, om träningen stoppades av överträningsdetektionen och körtid.
- [x] #9 Spridningen mellan upprepade körningar med samma inställningar är redovisad, så en skillnad mellan två inställningar kan skiljas från slumpen.
- [x] #10 Rapporten ligger i en markdown-fil med summering, resonemang, tabeller och grafer, och avslutas med en rekommendation om vilka variationer som är värda att använda vid ett tiotal bildpar.
- [x] #11 Manuellt skapade bilder och annoteringar i applikationen är oförändrade efter utvärderingen; modeller som tränats för utvärderingen får vara borttagna.
- [x] #12 Rapporten jämför resultatet med TASK-160:s YOLO-körning och säger om slutsatsen håller för RF-DETR large dvxray.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifiering:
- AC1-AC5: 29 körningar med vakten på, samma basmodell (checkpoint_best_total.pth), 100 epoker, imgsz 800 och batch 8. Baslinjen har synthetic_pairs 0; rotation, flip, scale och color körs var för sig; all-1 är kombinationen; antalet varieras i 1, 2, 5, 10 och 20.
- AC2: eval_fixed är samma fyra bilder som i TASK-160 (bild-id 29, 30, 43, 44) och rörs aldrig. RF-DETR-exporten delar träningsdelen i train/valid/test, så val-delen blir ett bildpar; det påverkar early stopping men inte mätningen.
- AC6: rapporten har en explicit rangordning och tabeller med mAP50-95, mAP50, mAP50-95 per vy och falska detektioner per bild.
- AC7: ingen kombination når baslinjen inom 1-20 variationer, så ingen övre gräns finns att fastställa.
- AC8: varje körning står i en tabell med train/val i par och bilder, epoker, om vakten stoppade den och körtid.
- AC9: spridningstabell per konfiguration. Baslinjens två körningar skiljer sig (0,069), så RF-DETR-träningen är inte deterministisk; det står i rapporten.
- AC11: användarens dataset är oförändrat: 20 bilder, 0 syntetiska, 53 objekt, samma updated-tidsstämpel. Alla modeller ligger i ~/.xray-detector/eval/.
- AC12: rapporten har ett eget avsnitt Jämförelse med YOLO-körningen.

Kontrollen med vakten av körde baslinje, rotation och färg med ett frön var (100 epoker). Färg gick från 0,000 till 0,228, alltså samma nivå som baslinjens 0,232; rotation gick från 0,007 till 0,159 och når inte baslinjen. Hela matrisen utan vakt skulle ta över tio timmar med RF-DETR large och kördes därför inte.

Tester: uv run pytest -q -p no:xdist gav 971 passed, 1 skipped. uv run ruff check . går igenom.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Samma utvärdering som TASK-160 är genomförd med RF-DETR large dvxray (models/checkpoint_best_total.pth) som basmodell. Rapporten ligger i docs/rapporter/bildvariationer-rfdetr.md med grafer i docs/rapporter/bilder/.

Vad som gjordes: scripts/variation_eval.py fick en --base som väljer export, träningsfamilj, arbetskatalog och rapportfil. 29 träningar kördes med appens egna moduler: baslinje, rotation, vändning, storlek och färg var för sig, alla fyra tillsammans, och kombinationen i 1, 2, 5, 10 och 20 variationer per bildpar, tre frön per konfiguration. Samma fasta utvärderingsuppsättning som i TASK-160 (bild-id 29, 30, 43, 44).

Resultat: baslinjen når mAP50-95 0,236 redan med överträningsvakten på, alltså en användbar modell där YOLO26 medium bara kom till 0,002. Ingen variationstyp slår baslinjen: alla fyra tillsammans 0,158, storlek 0,103, vändning 0,075, rotation 0,007 och färg 0,000. Spridningen är stor (upp till 0,138) eftersom RF-DETR-träningen inte är deterministisk, men riktningen är entydig.

Kontrollen med vakten av (baslinje, rotation och färg, 100 epoker) visar att färgens kollaps helt beror på att träningen stoppades: 0,228 mot baslinjens 0,232. Rotation återhämtar sig till 0,159 men når inte baslinjen, så den variationen skadar även vid full träning. Hela matrisen utan vakt skulle ta över tio timmar med RF-DETR large och kördes därför inte.

Slutsatsen från TASK-160 håller: vid ett tiotal annoterade bildpar är rekommendationen att träna på paren som de är och lägga arbetet på fler annoterade bildpar i stället.

Risker och uppföljning: utvärderingsuppsättningen är fyra bilder och tio objekt, så skillnader under ungefär 0,05 är brus. RF-DETR:s val-del blir ett bildpar, vilket gör early stopping extra känslig. Att vakten stoppar träningen på små dataset är fortfarande en egen fråga.
<!-- SECTION:FINAL_SUMMARY:END -->

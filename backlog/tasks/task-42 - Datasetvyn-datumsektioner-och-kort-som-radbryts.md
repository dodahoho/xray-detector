---
id: TASK-42
title: Dataset - datumsektioner och kort som radbryts
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T11:27:00Z'
updated_date: '2026-11-11T22:47:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/dataset_view.py
modified_files:
  - xray_detector/ui/dataset_view.py
  - tests/test_dataset_header.py
  - tests/test_dataset_layout.py
  - groma/systems/xray-detector/containers/gui-app/components/dataset-view.md
  - README.md
priority: medium
type: enhancement
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Dagens datasetvy lägger varje fångst i en egen fullbreddsruta med rubrik och två centrerade tumnaglar. Vid 1920 px fönsterbredd blir det två bilder per rad med stora tomma marginaler på båda sidor, så bara en bråkdel av ytan används och man får scrolla i onödan när datasetet växer.

Önskad struktur: en sektion per datum bilderna fångades, och inom sektionen ett kort per fångst med fångstens tid och dess två bilder. Korten läggs efter varandra på samma rad tills raden är full, då nästa rad börjas. Det ger tydlig separation mellan datum och bättre utnyttjande av skärmytan.

Dagens beteende som ska bevaras: bilderna hanteras alltid som ett par vid markering och borttagning (TASK-25), rubriken visar fångstens tid samt antal bilder och objekt (TASK-30), osparade fångster från pending-kön visas tydligt åtskilda (TASK-12), och dubbelklick öppnar annoteringsvyn.

Att väga in: fler synliga bilder betyder fler widgetar. Omladdningen tar i dag 580 ms för 200 bilder och skalar linjärt, så den nya layouten får inte bli långsammare.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Bilderna grupperas i en sektion per datum med datumet som rubrik
- [x] #2 Inom en sektion visas varje fångst som ett kort med fångstens tid och sina två bilder
- [x] #3 Korten läggs efter varandra på samma rad och radbryts när raden är full
- [x] #4 Vid samma fönsterbredd ryms minst fyra bilder per rad i stället för två
- [x] #5 Markering och borttagning markerar fortfarande hela paret
- [x] #6 Dubbelklick öppnar fortfarande annoteringsvyn för hela fångsten
- [x] #7 Osparade fångster visas fortfarande, tydligt åtskilda från sparade
- [x] #8 Rubriken visar fortfarande fångstens tid samt antal bilder och objekt
- [x] #9 Omladdningen är inte långsammare än i dag (580 ms för 200 bilder)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Ny xray_detector/ui/flow_layout.py: FlowLayout som lägger widgets efter varandra och radbryter när raden är full (heightForWidth), så korten kan flöda utan fasta kolumner.
2. dataset_view.py: fångsterna grupperas per datum. En sektion per datum med datumet som rubrik; inom sektionen ett kort per fångst med fångstens tid, antal bilder och objekt samt bildparet.
3. Korten läggs i FlowLayout och radbryts när raden är full, i stället för en fullbreddsruta per fångst.
4. Osparade fångster får en egen sektion överst (orange, streckade kort) med samma kortlayout, så de är tydligt åtskilda från sparade.
5. Behåll _thumbs/_groups/_group_headers, markering av hela paret, dubbelklick mot annoteringsvyn och borttagning; kortets rubrik och ram får markeringsstilen.
6. Tester: datumsektioner, kort per fångst, radbrytning (minst fyra bilder per rad vid 1920 px), osparad sektion, samt uppdaterade rubrik- och urvalstester.
7. Mät omladdningen med 200 bilder före och efter; den nya layouten får inte bli långsammare.
8. Uppdatera README och groma-komponenten dataset-view.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Layouten: datasetvyn bygger en sektion per datum (datumet som rubrik med underlinje) och ett kort per fångst i en FlowLayout som radbryts när raden är full. Kortet visar fångstens tid, antal bilder och objekt samt bildparet; rubriken och ramen får markeringsstilen som förut. Osparade fångster ligger i en egen sektion överst ("Osparade fångster", orange rubrik och streckade kort) och följer samma sortering. FlowLayout är en liten QLayout i dataset_view.py (Qt saknar flödeslayout) med heightForWidth, så korten radbryts om vid fönsterbredd. _thumbs/_groups/_group_headers finns kvar, så markering, borttagning och dubbelklick fungerar oförändrat.

Verifiering: 311 passed, 1 skipped (test_shortcut_on_inactive_tab_does_not_fire är flaky och passerar enskilt och i hela sviten). Nya tester i tests/test_dataset_layout.py: datumsektioner, ett kort per fångst med paret, radbrytning (minst fyra bilder per rad vid 1920 px, även 16:9), osparad sektion, sortering och okänt datum sist, samt FlowLayout-enhetstest. Mätt omladdning med 200 bilder (100 fångster, 5 datum): median 563 ms (560-565) mot 567 ms (566-572) före ändringen; _build 83-86 ms och layouten 46-47 ms. Vid 1920 px ryms 6 bilder per rad (3 kort) mot 2 före; vid 1000 px radbryts korten till 2 bilder per rad. Ruff: inga anmärkningar i ändrade filer.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Datasetvyn visar nu en sektion per datum med datumet som rubrik, och inom sektionen ett kort per fångst med fångstens tid, antal bilder och objekt samt bildparet. Korten ligger i en FlowLayout som radbryts när raden är full: vid 1920 px ryms 6 bilder per rad (3 kort) mot 2 före, och vid 1000 px radbryts de till 2. Osparade fångster ligger i en egen sektion överst med orange rubrik och streckade kort. Markering, borttagning och dubbelklick fungerar som förut eftersom _thumbs/_groups/_group_headers behölls.

Verifiering: 311 passed, 1 skipped; nya tester i tests/test_dataset_layout.py. Omladdningen med 200 bilder mäter median 563 ms mot 567 ms före ändringen, så den är inte långsammare. README och groma-komponenten dataset-view är uppdaterade.
<!-- SECTION:FINAL_SUMMARY:END -->

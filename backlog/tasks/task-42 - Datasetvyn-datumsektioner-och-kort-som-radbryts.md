---
id: TASK-42
title: 'Datasetvyn: datumsektioner och kort som radbryts'
status: To Do
assignee: []
created_date: '2026-11-11T11:27:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/dataset_view.py
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
- [ ] #1 Bilderna grupperas i en sektion per datum med datumet som rubrik
- [ ] #2 Inom en sektion visas varje fångst som ett kort med fångstens tid och sina två bilder
- [ ] #3 Korten läggs efter varandra på samma rad och radbryts när raden är full
- [ ] #4 Vid samma fönsterbredd ryms minst fyra bilder per rad i stället för två
- [ ] #5 Markering och borttagning markerar fortfarande hela paret
- [ ] #6 Dubbelklick öppnar fortfarande annoteringsvyn för hela fångsten
- [ ] #7 Osparade fångster visas fortfarande, tydligt åtskilda från sparade
- [ ] #8 Rubriken visar fortfarande fångstens tid samt antal bilder och objekt
- [ ] #9 Omladdningen är inte långsammare än i dag (580 ms för 200 bilder)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

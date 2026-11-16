---
id: TASK-101
title: Loggen saknar spår av vad appen gjorde vid uppstart
status: To Do
assignee: []
created_date: '2026-11-16T16:32:00Z'
labels: []
dependencies: []
priority: medium
type: enhancement
ordinal: 99000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-90. Appens enda loggkanal är `ui/main_window.py:140`, som loggar varje statusradsmeddelande som `status: %s`. 101 av 183 rader i `logs/app.log` är sådana avskrifter, så loggen beskriver statusraden i stället för appen. Inget loggar vilken konfigfil som användes och vad den innehöll, vilken enhet som valdes, vilken viktfil som laddades och hur lång tid det tog, datasetets storlek vid start eller kamerauppräkningens resultat. Gapet mellan `Startar X-ray detector` (15:09:23,671) och `Modell laddad` (15:09:33,548) är tio sekunder som loggen inte förklarar alls. Dessutom saknar loggformatet process-id, trots att träningen körs i en separat OS-process (TASK-6), och app.log och training.log har inget gemensamt id så en träningskörning går inte att följa mellan filerna.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Uppstarten loggar vilken konfigfil som användes och vilka värden den satte
- [ ] #2 Modelladdning loggar viktfil, familj, enhet och tidsåtgång
- [ ] #3 Datasetets storlek och kamerauppräkningens resultat loggas vid start
- [ ] #4 Loggformatet innehåller process-id
- [ ] #5 En träningskörning har ett id som går att hitta i både app.log och training.log
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

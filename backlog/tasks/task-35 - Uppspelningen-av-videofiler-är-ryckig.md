---
id: TASK-35
title: Uppspelningen av videofiler är ryckig
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T13:18:00Z'
updated_date: '2026-11-10T15:16:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Undersök orsak och åtgärda om det går att få uppspelningen smooth
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Orsaken till den ryckiga uppspelningen är identifierad och dokumenterad
- [ ] #2 Uppspelningen håller videons bildfrekvens utan att driva
- [ ] #3 Ändringen gör inte testsviten mer instabil
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Utredning klar: pacingen i FileSource.read() driver 0,64 % för långsamt eftersom sleep-överslaget läggs till varje ram.
2. Fixen är deadline-baserad pacing: _deadline += _frame_interval varje ram i stället för att räkna från föregående läsning.
3. Fixen är blockerad av TASK-34: den gör testsvitkraschen deterministisk (3/3 mot 3/3 gröna på HEAD).
4. När TASK-34 är löst: applicera fixen, verifiera 33,55 -> 33,28 ms i displaymätningen och lägg till tester för pacingen.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Utredning på de nya demovideorna (1280x720@30 fps, 2250 ramar).

VAR TIDEN GÅR (mätt):
- Avkodning: 0,84 ms/ram, std 0,09, max 1,35. Mycket stabil, inte orsaken.
- StreamPanel.show_frame (cvtColor + QPainter + skalning + setPixmap): 1,84 ms/ram; GUI-tråden ligger på 10,9 % av en kärna. Inte flaskhalsen.
- ResourceMonitor.sample() (körs varje sekund på GUI-tråden): 0,097 ms varm. Första anropet tar 1,2 s (CUDA-kontexten), men i appen är den redan initierad av detektorn.
- Panelens etikettstorlek är stabil mellan ramar (844x784, pixmap 844x474), så skalningen oscillerar inte.

ORSAKEN: pacingen i FileSource.read() driver. Väntetiden räknas från föregående läsning och _last_read sätts till den faktiska tiden efter sleep, så sleep-överslaget (cirka 0,3 ms per ram) läggs till varje ram. Uppmätt period blir 33,55 ms i stället för 33,33, alltså 0,64 % för långsamt: 29,75 fps i stället för 30. Fasen driver mot skärmens 60 Hz-uppdatering och var ~2,6 s får en ram tre uppdateringar i stället för två, vilket syns som periodiska hack.

ÅTGÄRD SOM FUNGERAR MEN ÄR BLOCKERAD: deadline-baserad pacing (_deadline += _frame_interval varje ram) ger 33,28 ms i snitt, alltså rätt hastighet, och std sjunker från 1,55 till 1,42 ms. Men ändringen gör den kända testsvitkraschen (TASK-34) deterministisk: 3 av 3 körningar kraschar med ändringen mot 3 av 3 gröna på HEAD, interleaved samma minut. Jag provade även inline-variant, långsammare pacing (+0,25 ms per ram) och att ta bort deadline-reset i _open(); alla kraschade. Orsaken till samverkan är inte klarlagd, så ändringen är backad och ingen kod är ändrad.

NÄSTA STEG: lös TASK-34 först. Därefter är pacing-fixen cirka 10 rader i FileSource.read() och kan verifieras med samma mätning (33,55 -> 33,28 ms).

Blockeraren är löst: TASK-34 är klar och testsviten går 10 av 10 grönt. Jag verifierade pacing-ändringen med fixen applicerad: 3 av 3 gröna körningar, mot 3 av 3 krascher innan. Ändringen är cirka 10 rader i FileSource.read() (byt _last_read mot en _deadline som flyttas fram exakt en ram i taget) och gav 33,55 -> 33,28 ms i displaymätningen. Uppgiften är redo att plockas upp.
<!-- SECTION:NOTES:END -->

---
id: TASK-35
title: Uppspelningen av videofiler är ryckig
status: Done
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T13:18:00Z'
updated_date: '2026-11-10T16:39:00Z'
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
- [x] #1 Orsaken till den ryckiga uppspelningen är identifierad och dokumenterad
- [x] #2 Uppspelningen håller videons bildfrekvens utan att driva
- [x] #3 Ändringen gör inte testsviten mer instabil
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

Implementerat: FileSource.read() använder nu en deadline som flyttas fram exakt en _frame_interval per ram i stället för att räkna väntetiden från föregående läsning. Deadlinen nollställs i _open() och vid loop (frame is None), och om vi ligger efter startas den om från nu i stället för att spara skuld.

Verifiering: displaymätning över 12 s i tre körningar: period 33,277 / 33,284 / 33,288 ms i snitt och 33,332 / 33,336 / 33,290 i median, mot 33,55 före. Medianen ligger nu på videons exakta 33,333 ms, alltså ingen drift, och std sjönk från 1,55 till 1,44 ms. 359 ramar på 12 s = 29,9 fps mot 29,75 före.

Två nya tester i tests/test_stream_worker.py: pacingen håller videons bildfrekvens över 30 ramar, och deadlinen flyttas exakt en ram i taget (time.sleep monkeypatchas bort så mätningen blir deterministisk).

Hela sviten 10 av 10 gröna med 149 passed, 1 skipped — två fler tester än före och ingen krasch, tack vare TASK-34.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Videouppspelningen driver inte längre. FileSource räknade väntetiden från föregående läsning och satte klockan till den faktiska tiden efter sleep, så sleep-överslaget lades till varje ram: perioden blev 33,55 ms i stället för 33,33, alltså 29,75 fps i stället för 30, och fasen drev mot skärmens uppdatering. Nu flyttas en deadline fram exakt en ram i taget.

Verifierat: period 33,28 ms i snitt och 33,33 i median (videons exakta), std 1,44 ms mot 1,55 före. Två nya tester. Hela sviten 10 av 10 gröna, 149 passed, 1 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->

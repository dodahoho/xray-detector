---
id: TASK-37
title: Uppspelningen av videofiler är ryckig trots åtgärderna i task-35
status: Done
assignee: []
created_date: '2026-11-10T16:52:00Z'
updated_date: '2026-11-10T17:08:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Uppspelningen av videofiler som källa i applikationen blir ryckig trots de åtgärder som gjordes i task-35.

Hur kan det göras på ett bättre sätt? Läsa in och buffra frames innan visning? Finns det ramverk/moduler i python som hanterar uppspelning av media bättre? Kan åtgärderna i task-10 ha påverkat jämnheten i uppspelningshastigheten?
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Orsaken till ryckigheten är identifierad och dokumenterad
- [x] #2 Uppspelningen håller jämn takt utan synliga hack
- [x] #3 Inga ramar tappas eller visas i fel ordning
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
Utredning: uppspelningen tappade inga ramar (313 emitterade = 313 visade, inga luckor i sekvensnumren) och höll rätt takt (30,09 fps), men visningsintervallen varierade 25-42 ms. Jittret satt i worker-tråden, inte i GUI:t: worker-emit std 2,76 ms mot GUI-visning std 3,11 ms, med bara 2,73 ms latens och 1,01 ms spridning mellan dem.

Isolering: med en detektor som tar konstant tid (0 eller 7 ms) blev worker-emit std 0,32-0,40 ms och p5-p95 32,7-33,9 ms. Med den riktiga YOLO-detektorn (6-9 ms, varierande) blev std 2,86 ms och p5-p95 27,7-39,0. Alltså: detektionens varierande körtid förskjuter visningen, eftersom StreamWorker körde detect() före frame_ready.emit.

Åtgärd: ramen emitteras nu direkt efter avkodningen och detektionen körs efteråt. Ramen bär föregående frames detektioner, så overlayn ligger en ram efter bilden.

Mätning efter: worker-emit std 0,29 ms, p5-p95 32,9-33,8. Hela vägen till skärmen: 30,00 fps, std 1,03 ms, intervall 31,1-35,5 ms, mot 3,11 ms och 16,8-42,4 ms före.

Svar på frågorna i uppgiften:
- Buffra frames innan visning: behövs inte. GUI-tråden ligger på 10,9 % av en kärna och inga ramar tappas; flaskhalsen var timingen i worker-tråden, inte genomströmningen.
- Ramverk för mediauppspelning: QMediaPlayer/VLC/mpv kan inte lämna ut råa ramar till inferensen, så de är inte användbara här. PyAV ger bättre tidsstämpelkontroll men löser inte att detektionen ligger i samma tråd som avkodningen.
- TASK-10: påverkade inte. CAP_PROP_BUFFERSIZE=1 sätts bara i UvcSource, och FPS-fönstret plus sekvensnumret är några aritmetiska operationer per ram.

Verifiering: 1 nytt test (ramen emitteras innan detektionen), hela sviten 155 passed, 1 skipped, 3 av 3 gröna.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Uppspelningen hackade för att StreamWorker körde detektionen före frame_ready.emit: ramens visningstid blev deadline + avkodning + detektion, och detektionens körtid varierar mellan ramar. Mätt med en detektor som tar konstant tid var jittret 0,32 ms; med YOLO26m 2,86 ms. Nu emitteras ramen direkt efter avkodningen och detektionen körs efteråt.

Verifierat: worker-emit std 0,29 ms (p5-p95 32,9-33,8) och hela vägen till skärmen 30,00 fps med std 1,03 ms, mot 3,11 ms och intervall 16,8-42,4 ms före. Inga ramar tappas. Overlayn ligger en ram efter bilden, vilket utjämningen i TASK-33 redan maskerar.

Frågorna i uppgiften: buffring behövs inte (GUI:t är inte flaskhalsen), QMediaPlayer/VLC/mpv kan inte lämna ut råa ramar till inferensen, och TASK-10 påverkade inte (BUFFERSIZE sätts bara för UVC).
<!-- SECTION:FINAL_SUMMARY:END -->

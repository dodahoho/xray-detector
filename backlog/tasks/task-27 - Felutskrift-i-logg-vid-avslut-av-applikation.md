---
id: TASK-27
title: Felutskrift i logg vid avslut av applikation
status: Done
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T08:58:00Z'
updated_date: '2026-11-10T09:11:00Z'
labels: []
dependencies: []
type: bug
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Vad beror felutskriften på? Åtgärda

Följande står i loggen:
I2026-11-10 09:56:38.181603 (13784) [INFO] [VCAMDS] Destroying parent object
I2026-11-10 09:56:38.182607 (13784) [INFO] [VCAMDS] Destroying WndMsg Listener Window
E2026-11-10 09:56:38.182607 (13784)  [ERR] [VCAMDS] Failed to destroy the window
I2026-11-10 09:56:38.182607 (13784) [INFO] [VCAMDS] Unregistered window class
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Källan stängs i den arbetstråd som öppnade den, så drivrutinens fönster rivs från rätt tråd
- [x] #2 Ingen tråd tvingas till terminate vid normal avslutning (start/stopp-racet är borta)
- [x] #3 Kameran släpps innan fönstret stängs
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
1. StreamWorker: stäng källan i run()s finally, så cv2.VideoCapture.release() sker i den tråd som öppnade den (DSHOW-fönstret ägs av den tråden).
2. StreamWorker: sätt _running = True i __init__ i stället för i run(), så stop() direkt efter start() inte kan fastna i en oändlig loop som tvingar terminate().
3. stop(): behåll en close() som fallback om tråden måste termineras.
4. Tester: källan stängs i arbetstråden, stop() direkt efter start() avslutar snabbt.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rotorsak: cv2.VideoCapture.release() anropades från GUI-tråden (StreamWorker.stop -> source.close) medan källan öppnats i arbetstråden. DSHOW-fönstret som drivrutinen skapar ägs av den tråden, så rivningen skedde från fel tråd — det är vad drivrutinen rapporterar som 'Failed to destroy the window'. Dessutom satte run() _running = True, så stop() direkt efter start() kunde fastna i en loop som aldrig avslutades: wait(5000) time-outade och terminate() dödade tråden mitt i en läsning.

Ändringar: källan stängs nu i run()s finally, alltså i den tråd som öppnade den. _running sätts i __init__ i stället för i run(), och run() returnerar direkt om stop() redan hunnit köra. stop() behåller en close() som fallback om tråden måste termineras.

Verifiering: tre nya tester i tests/test_stream_worker.py. Mot den gamla koden faller alla tre (close_thread != open_thread, stop() tog 5,02 s och tvingade terminate); med fixen går hela sviten 122 passed, 1 skipped. DoD #4: ingen användardokumentation påverkas — invarianten dokumenteras i kodkommentaren i run(). De VCAMDS-rader drivrutinen själv skriver kan appen inte tysta; fixen tar bort appens andel av dem.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Kamerakällan stängs nu i den arbetstråd som öppnade den i stället för i GUI-tråden, vilket är det som fick drivrutinen att logga 'Failed to destroy the window' vid avslut. Start/stopp-racet är också borta: _running sätts i __init__, så stop() direkt efter start() avslutar tråden i stället för att tvinga fram wait(5000)-timeout och terminate().

Verifierat: tre nya tester som faller mot den gamla koden (fel tråd vid close, 5,02 s stopp) och passerar med fixen; hela sviten 122 passed, 1 skipped. De VCAMDS-rader som drivrutinen själv skriver kan appen inte tysta — fixen tar bort appens andel av dem.
<!-- SECTION:FINAL_SUMMARY:END -->

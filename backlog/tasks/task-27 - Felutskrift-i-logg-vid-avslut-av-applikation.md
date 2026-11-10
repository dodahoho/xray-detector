---
id: TASK-27
title: Felutskrift i logg vid avslut av applikation
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T08:58:00Z'
updated_date: '2026-11-10T09:09:00Z'
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
- [ ] #1 Källan stängs i den arbetstråd som öppnade den, så drivrutinens fönster rivs från rätt tråd
- [ ] #2 Ingen tråd tvingas till terminate vid normal avslutning (start/stopp-racet är borta)
- [ ] #3 Kameran släpps innan fönstret stängs
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
1. StreamWorker: stäng källan i run()s finally, så cv2.VideoCapture.release() sker i den tråd som öppnade den (DSHOW-fönstret ägs av den tråden).
2. StreamWorker: sätt _running = True i __init__ i stället för i run(), så stop() direkt efter start() inte kan fastna i en oändlig loop som tvingar terminate().
3. stop(): behåll en close() som fallback om tråden måste termineras.
4. Tester: källan stängs i arbetstråden, stop() direkt efter start() avslutar snabbt.
<!-- SECTION:PLAN:END -->

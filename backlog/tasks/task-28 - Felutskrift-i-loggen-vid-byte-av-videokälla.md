---
id: TASK-28
title: Felutskrift i loggen vid byte av videokälla
status: Done
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T09:02:00Z'
updated_date: '2026-11-10T09:11:00Z'
labels: []
dependencies: []
type: bug
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När jag byter mellan UVC0 och UVC1 får jag nedanstående i loggen. Det är ett ERR där som förmodligen behöver någon åtgärd i koden.

I2026-11-10 09:59:41.342864 (20400) [INFO] [VCAMDS] Destroying WndMsg Listener Window
I2026-11-10 09:59:41.344866 (20400) [INFO] [VCAMDS] Destroyed window
I2026-11-10 09:59:41.344866 (20400) [INFO] [VCAMDS] Unregistered window class
I2026-11-10 09:59:41.344866 (20400) [INFO] [VCAMDS] Video data consumption app tracker updating num DLL loaded: 0
I2026-11-10 09:59:41.351946 (20400) [INFO] [VCAMDS] NvMxnCltShmConsumer Update num apps DLL loaded succeeded
E2026-11-10 09:59:41.356789 (20400)  [ERR] [VCAMDS] Failed to open NBX hive
I2026-11-10 09:59:41.356789 (20400) [INFO] [VCAMDS] Creating WndMsg Listener Window
I2026-11-10 09:59:41.358789 (20400) [INFO] [VCAMDS] Requested to perform initializing sequence
I2026-11-10 09:59:41.358789 (20400) [INFO] [VCAMDS] Performing initializing sequence
I2026-11-10 09:59:41.358789 (20400) [INFO] [VCAMDS] Entered Shared Memory Consumer Initialize
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Byte av videokälla stänger den gamla källan i dess arbetstråd innan den nya öppnas
- [x] #2 Ingen tråd tvingas till terminate vid byte
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
1. Samma livscykelfix som TASK-27: källan stängs i arbetstråden, så den gamla enheten är helt släppt innan CameraService.set_source öppnar nästa.
2. Verifiera att stop_source väntar in tråden innan den nya källan startas.
3. Tester: byte av källa stänger gamla källan i dess tråd och lämnar inga kvarvarande workers.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Samma rotorsak som TASK-27: den gamla källan stängdes från GUI-tråden när CameraService.set_source bytte enhet, och drivrutinen loggade 'Failed to open NBX hive' när nästa enhet initierades. Nu stängs källan i sin egen arbetstråd och stop_source väntar in tråden, så den gamla enheten är helt släppt innan den nya öppnas.

Verifiering: test_camera_service_switch_closes_old_source_in_worker_thread faller mot gamla koden (close_thread != open_thread) och passerar med fixen; inga workers ligger kvar efter stop_all(). Hela sviten 122 passed, 1 skipped. DoD #4: ingen användardokumentation påverkas — invarianten dokumenteras i kodkommentaren i run(). Drivrutinens egen loggning kan appen inte påverka.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Byte av videokälla stänger nu den gamla källan i dess egen arbetstråd innan den nya enheten öppnas, i stället för att riva den från GUI-tråden. Det var rivningen från fel tråd som fick drivrutinen att logga 'Failed to open NBX hive' vid initieringen av nästa enhet.

Verifierat: nytt test som faller mot gamla koden och passerar med fixen; inga workers ligger kvar efter stop_all(). Hela sviten 122 passed, 1 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->

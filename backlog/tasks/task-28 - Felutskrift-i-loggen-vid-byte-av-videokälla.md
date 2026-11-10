---
id: TASK-28
title: Felutskrift i loggen vid byte av videokälla
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T09:02:00Z'
updated_date: '2026-11-10T09:09:00Z'
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
- [ ] #1 Byte av videokälla stänger den gamla källan i dess arbetstråd innan den nya öppnas
- [ ] #2 Ingen tråd tvingas till terminate vid byte
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
1. Samma livscykelfix som TASK-27: källan stängs i arbetstråden, så den gamla enheten är helt släppt innan CameraService.set_source öppnar nästa.
2. Verifiera att stop_source väntar in tråden innan den nya källan startas.
3. Tester: byte av källa stänger gamla källan i dess tråd och lämnar inga kvarvarande workers.
<!-- SECTION:PLAN:END -->

---
id: TASK-31
title: Se hårdvaruresurser i realtid
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T11:48:00Z'
updated_date: '2026-11-10T11:50:00Z'
labels: []
dependencies: []
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
I detektionsläge skulle det vara trevligt att se applikationens aktuella användning av GPU, VRAM, CPU, RAM. Kanske i form av staplar ovanflr fönstret, efter texten med enhet CUDA
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Detektionsläget visar aktuell GPU-, VRAM-, CPU- och RAM-användning som staplar
- [ ] #2 Staplarna sitter i den övre raden efter enhetsetiketten och uppdateras löpande
- [ ] #3 Utan CUDA visas GPU och VRAM som n/a i stället för att appen kraschar
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
1. ResourceMonitor i infrastructure/system samplar appens CPU/RAM via psutil och GPU/VRAM via torch.cuda (utilization, memory_allocated, total_memory).
2. ResourceMeter-widget (etikett + QProgressBar + värde) i detektionsvyn, fyra stycken efter enhetsetiketten.
3. QTimer på 1 s uppdaterar staplarna; GPU/VRAM visar n/a utan CUDA.
4. psutil läggs till som explicit beroende.
5. Tester: monitor-snapshot, meter-formatering, detektionsvyns uppdatering med fejkad monitor.
<!-- SECTION:PLAN:END -->

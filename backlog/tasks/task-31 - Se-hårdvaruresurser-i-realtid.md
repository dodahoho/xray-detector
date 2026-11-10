---
id: TASK-31
title: Se hårdvaruresurser i realtid
status: Done
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T11:48:00Z'
updated_date: '2026-11-10T11:53:00Z'
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
- [x] #1 Detektionsläget visar aktuell GPU-, VRAM-, CPU- och RAM-användning som staplar
- [x] #2 Staplarna sitter i den övre raden efter enhetsetiketten och uppdateras löpande
- [x] #3 Utan CUDA visas GPU och VRAM som n/a i stället för att appen kraschar
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
1. ResourceMonitor i infrastructure/system samplar appens CPU/RAM via psutil och GPU/VRAM via torch.cuda (utilization, memory_allocated, total_memory).
2. ResourceMeter-widget (etikett + QProgressBar + värde) i detektionsvyn, fyra stycken efter enhetsetiketten.
3. QTimer på 1 s uppdaterar staplarna; GPU/VRAM visar n/a utan CUDA.
4. psutil läggs till som explicit beroende.
5. Tester: monitor-snapshot, meter-formatering, detektionsvyns uppdatering med fejkad monitor.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Ny ResourceMonitor i xray_detector/infrastructure/system/resources.py samplar appens CPU och RSS via psutil.Process(), GPU-utnyttjande via torch.cuda.utilization() och VRAM via torch.cuda.memory_allocated()/get_device_properties().total_memory. Alla fält är None när resursen inte kan mätas, så anroparen slipper undantag.

Detektionsvyn har fyra ResourceMeter-widgets (etikett + QProgressBar + värde) i den övre raden efter enhetsetiketten, uppdaterade av en QTimer på 1 s. CPU normaliseras mot antalet kärnor: psutil räknar process-CPU per kärna och kan rapportera 200 %, vilket gjorde stapeln missvisande. GPU/VRAM visar 'n/a' utan CUDA. psutil är nu ett explicit beroende i pyproject.toml (>=5.9) i stället för en transitiv sådan via ultralytics.

Verifiering: 7 nya tester i tests/test_resources.py (monitor-sampling, byteformatering, meter med/utan värde, detektionsvyns fyra staplar, riktiga värden och n/a utan GPU). Hela sviten 136 passed, 1 skipped. Riktig körning: första samplingen visade gpu 0 %, vram 0 B / 15.9 GB, cpu 4 %, ram 585 MB; efter att 256 MB allokerats på GPU:n visade vram 256.0 MB / 15.9 GB och stapeln flyttade sig. Skärmbilden renderades 1756x500.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Detektionsläget visar nu appens GPU-, VRAM-, CPU- och RAM-användning som fyra staplar i den övre raden efter enhetsetiketten, uppdaterade varje sekund. En ny ResourceMonitor samplar CPU/RAM via psutil och GPU/VRAM via torch.cuda; CPU normaliseras mot antalet kärnor så stapeln visar andel av maskinen, och GPU/VRAM visar n/a utan CUDA. psutil är nu ett explicit beroende.

Verifierat: 7 nya tester; hela sviten 136 passed, 1 skipped. Riktig körning visade vram 0 B -> 256.0 MB när 256 MB allokerades på GPU:n, medan cpu låg på 3-4 % av maskinen.
<!-- SECTION:FINAL_SUMMARY:END -->

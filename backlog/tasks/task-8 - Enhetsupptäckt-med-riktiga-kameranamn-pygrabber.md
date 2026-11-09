---
id: TASK-8
title: Enhetsupptäckt med riktiga kameranamn (pygrabber)
status: Done
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-09T09:45:00Z'
labels:
  - video
  - ux
  - windows
dependencies: []
references:
  - detection-view
  - video-capture
modified_files:
  - xray_detector/infrastructure/video/devices.py
  - xray_detector/application/video_service.py
  - xray_detector/ui/detection_view.py
  - pyproject.toml
  - uv.lock
  - tests/test_devices.py
priority: medium
type: enhancement
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Detektionsvyns källval hårdkodar UVC 0 och UVC 1. opencode-bigpickle har device_discovery som använder pygrabber.dshow_graph.FilterGraph på Windows för att lista faktiska enhetsnamn, med prohibefallback (öppnar index kort) om pygrabber saknas. Se jämförelse_glm53.md punkt 1.

Implementera xray_detector/capture/devices.py med list_devices(); fyll källmenyn i detection_view.py med riktiga namn istället för index; behåll valet att öppna videofil.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 källrullgardinsmenyn listar anslutna kameror med deras riktiga namn
- [x] #2 fungerar utan pygrabber installerat (fallback till indexprobe)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ny infrastructure-modul devices.py listar UVC-enheter med riktiga namn via pygrabber.dshow_graph pa Windows (optional-dependency windows); utan pygrabber faller den tillbaka pa index 0/1 utan att oppna nagon kamera. VideoService.list_devices() ar applikationsfasaden och detektionsvynns strampaneler bygger kallmenyn fran listan ('UVC 0 - Logitech...' etc.). Combo-dispatchen ar nu databaserad (strang-data 'uvc:<index>'/'file'/'none') sa persistens och restore fungerar oberoende av namntexten. Verifierat: 7 nya tester (namnlistning, fallback, felhandtering, comboinnehall, val som signal, restore via data, fallback-panel); hela sviten 37 passed.
<!-- SECTION:FINAL_SUMMARY:END -->

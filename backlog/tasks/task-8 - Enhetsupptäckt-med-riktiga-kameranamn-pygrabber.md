---
id: TASK-8
title: Enhetsupptäckt med riktiga kameranamn (pygrabber)
status: In Progress
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-09T09:36:00Z'
labels:
  - video
  - ux
  - windows
dependencies: []
references:
  - detection-view
  - video-capture
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
- [ ] #1 källrullgardinsmenyn listar anslutna kameror med deras riktiga namn
- [ ] #2 fungerar utan pygrabber installerat (fallback till indexprobe)
<!-- AC:END -->

---
id: TASK-55
title: Detektionsvy titel i videofönster
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T19:38:00Z'
updated_date: '2026-11-11T19:51:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 53000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ny står Ström 1 och namn på videofil (om det är valt) längst upp till vänster i titelrad för videokälla innan framerate i fps.
Ta bort det som står innan framerate så att det blir mindre info där, mer cleant
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Raden ovanför videobilden visar bara strömmens bildfrekvens i fps
- [x] #2 "Ström 1"/"ström 2" och videofilens namn syns inte längre i raden
- [x] #3 Etiketten töms när ingen källa är vald
- [x] #4 README och groma-arkitekturen beskriver den nya raden
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
1. detection_view.py: StreamPanel tappar title-parametern och _base_title; etiketten blir fps_label som bara visar bildfrekvensen ("29.3 fps") och töms när ingen fps finns.
2. _show_no_source() rensar fps-etiketten i stället för att sätta en panelrubrik.
3. Tester: test_stream_worker.py och test_video_source_persistence.py verifierar att bara fps står i raden; StreamPanel-anropen i test_devices.py, test_reconnect.py, test_sample_video.py och test_video_modes.py följer den nya signaturen.
4. README: en mening om att panelens rad bara visar bildfrekvensen.
5. groma: detection-view.md uppdateras via groma edit.
6. Verifiering: hela testsviten och ruff på ändrade filer.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
StreamPanel har ingen rubrik längre: title-parametern och _base_title är borta, och etiketten heter fps_label. show_frame sätter den till "29.3 fps" och _show_no_source tömmer den, så raden ovanför bilden innehåller bara bildfrekvensen. Källans namn syns i källväljaren, som redan visar "Videofil: x.mp4" eller "UVC 0 · Logitech C920".

Tester: test_panel_title_shows_fps -> test_panel_title_shows_only_fps (exakt "29.3 fps", tom utan fps) och test_title_shows_active_file_and_fps -> test_title_row_shows_only_fps (filnamnet syns inte längre i raden). StreamPanel-anropen i test_devices.py, test_reconnect.py, test_sample_video.py och test_video_modes.py följer den nya signaturen.

Verifiering: hela sviten 242 passed, 1 skipped (samma som före ändringen). ruff rapporterar 15 fynd i de berörda filerna, alla befintliga och utanför de ändrade raderna. Panelen är granskad visuellt via QWidget.grab(): raden visar "29.5 fps" till vänster och källväljaren till höger, utan "Ström 1" och utan filnamn.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Raden ovanför videobilden i varje strömpanel visar nu bara strömmens bildfrekvens, till exempel "29.5 fps". "Ström 1"/"ström 2" och videofilens namn är borta ur raden: filnamnet syns ändå i källväljaren ("Videofil: x.mp4"), så informationen finns kvar där den hör hemma och raden blir kortare.

Ändringar: StreamPanel i xray_detector/ui/detection_view.py tappar title-parametern och _base_title, och etiketten title_label heter nu fps_label. show_frame sätter den till fps-texten och _show_no_source tömmer den. Testerna test_panel_title_shows_only_fps och test_title_row_shows_only_fps verifierar exakt innehåll i stället för delsträngar, och StreamPanel-anropen i test_devices.py, test_reconnect.py, test_sample_video.py och test_video_modes.py följer den nya signaturen. README:s avsnitt Lägen och groma-arkitekturen (detection-view.md) beskriver den nya raden.

Verifiering: hela sviten 242 passed, 1 skipped, samma som före ändringen. ruff rapporterar 15 fynd i de berörda filerna, alla befintliga och utanför de ändrade raderna. Panelen är granskad visuellt via QWidget.grab(): raden visar "29.5 fps" till vänster och källväljaren till höger.

Risk: panelerna har ingen rubrik kvar, så två strömmar skiljs bara åt av källväljarens innehåll. Det var vad uppgiften bad om, men om panelerna senare får olika roller (till exempel sidovy och toppvy) kan en kort rubrik behövas igen.
<!-- SECTION:FINAL_SUMMARY:END -->

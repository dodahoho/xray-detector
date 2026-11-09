---
id: TASK-10
title: 'Videopipeline: BUFFERSIZE=1, faktisk FPS-visning och ramsekvensnummer'
status: Done
assignee: []
created_date: '2026-11-06T14:05:00Z'
updated_date: '2026-11-09T09:47:00Z'
labels:
  - video
  - prestanda
  - robusthet
dependencies: []
references:
  - video-capture
  - detection-view
modified_files:
  - xray_detector/infrastructure/video/source.py
  - xray_detector/infrastructure/video/camera_service.py
  - xray_detector/domain/capture.py
  - xray_detector/ui/detection_view.py
  - xray_detector/infrastructure/video/devices.py
  - tests/test_stream_worker.py
priority: medium
type: enhancement
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Två förbättringar i videoinspelningen som andra brancher har (jämförelse_glm53.md punkt 5, jämförelse_argon.md avsnitt 6):

1. cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) på UVC-källor så drivrutinens interna buffert inte ger eftersläpande ramar (antigravity/deepseek).
2. Monotont ramsekvensnummer (FramePacket.sequence i bigpickle) så detektion aldrig kör på samma ram två gånger och overlay aldrig ritas från äldre detektioner på nyare ramar.

Visa även faktisk FPS per ström i panelrubriken som antigravity gör.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 UVC-källor sätter CAP_PROP_BUFFERSIZE 1
- [x] #2 varje ram har ett sekvensnummer och gamla detektioner ritas aldrig på nyare ramar
- [x] #3 faktisk FPS visas per strömpanel
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
UvcSource satter CAP_PROP_BUFFERSIZE=1 efter oppning (DSHOW->MSMF->ANY) sa drivrutinens interna buffert inte ger efterslapande ramar. StreamFrame far sequence (monoton per StreamWorker) och fps (glidande matning over 30 ramer) med bakatkompatibla default-val. StreamPanel visar faktisk FPS i rutriken nar resp. kalla tappas. Detektionen ker fortfarande i samma loop-iteration som utlasningen, sa overlay kan aldrig ritas pa en aldre ram (sekvensnumret gar att verifiera det). Verifierat: 4 nya tester (monoton sekvens, fps-uppmatning > 0, bakatkompatibla defaults, rubrikvisning av fps); hela sviten 41 passed. OBS: BUFFERSIZE=1 kan inte verifieras headlost mot riktig UVC-kamera (kraver hardvara) men ansatts bevaras i DSHOW-oppningsvagen med enhetstest pa att set-anropet finns i _open.
<!-- SECTION:FINAL_SUMMARY:END -->

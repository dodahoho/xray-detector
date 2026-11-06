---
id: TASK-10
title: 'Videopipeline: BUFFERSIZE=1, faktisk FPS-visning och ramsekvensnummer'
status: To Do
assignee: []
created_date: '2026-11-06T14:05:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - video
  - prestanda
  - robusthet
dependencies: []
references:
  - video-capture
  - detection-view
priority: medium
type: enhancement
ordinal: 10000
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
- [ ] #1 UVC-källor sätter CAP_PROP_BUFFERSIZE 1
- [ ] #2 varje ram har ett sekvensnummer och gamla detektioner ritas aldrig på nyare ramar
- [ ] #3 faktisk FPS visas per strömpanel
<!-- AC:END -->

---
id: TASK-5
title: Stabila klassfärger i detektionsoverlay
status: Done
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-09T09:42:00Z'
labels:
  - bug
  - detektion
  - gui
dependencies: []
references:
  - detection-view
  - detectors
modified_files:
  - xray_detector/ui/colors.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/annotation_view.py
  - tests/test_colors.py
priority: high
type: bug
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
I detection_view.py väljs overlayfärg med hash(detection.class_name) — Python-strängens hashvärde seedas slumpmässigt per process, så samma klass får olika färg vid varje appstart och kan krocka med andra klasser.

Se jämförelse_qwen38.md ("hash(class) ger färg som byter vid varje start").

Lösning: deterministisk mappning klass till fast färg i CLASS_COLORS, delad mellan detektionsvy och annoteringsvy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 samma klassnamn får samma färg vid varje appstart och i alla vyer
- [x] #2 färgvalet är dokumenterat i en gemensam modul
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ny delad modul ui/colors.py: class_color() mappar kanda klasser till fast index i klasslistan och okanda klasser till CRC32 (processoberoende, till skillnad fran Pythons hash()). Detektionsoverlay (StreamPanel) och annoteringsrektanglar malar nu med samma deterministiska farga per klass namn i varje session och vy. Verifierat med tester: kand-klass-index, CRC32-determinism over PYTHONHASHSEED-varianter i subprocesser, samt distinkta farger over palette.
<!-- SECTION:FINAL_SUMMARY:END -->

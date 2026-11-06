---
id: TASK-5
title: Stabila klassfärger i detektionsoverlay
status: To Do
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - bug
  - detektion
  - gui
dependencies: []
references:
  - detection-view
  - detectors
priority: high
type: bug
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
I detection_view.py väljs overlayfärg med hash(detection.class_name) — Python-strängens hashvärde seedas slumpmässigt per process, så samma klass får olika färg vid varje appstart och kan krocka med andra klasser.

Se jämförelse_qwen38.md ("hash(class) ger färg som byter vid varje start").

Lösning: deterministisk mappning klass till fast färg i CLASS_COLORS, delad mellan detektionsvy och annoteringsvy.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 samma klassnamn får samma färg vid varje appstart och i alla vyer
- [ ] #2 färgvalet är dokumenterat i en gemensam modul
<!-- AC:END -->

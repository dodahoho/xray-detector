---
id: TASK-103
title: >-
  Träningsvy - Dataset som ett eget card i sidan till höger om de generella
  träningsparametrarna
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-16T20:55:00Z'
updated_date: '2026-11-16T21:01:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 101000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Skapa ett eget card för dataset och lägg dit texten om dataset storlek samt train/val split
Flytta även inställningar för andel trin/val från separata inställningsdialogen till detta nya card
<!-- SECTION:DESCRIPTION:END -->

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
1. Dela träningsvyns överkant i en rad med två kort: Träningsinställningar till vänster och ett nytt Dataset-kort till höger, båda med FormCard:s maxbredd.
2. Flytta sammanställningen (dataset_info) till Dataset-kortet och lägg andelen train/val där som ett eget fält med ledtext.
3. Ta bort TrainValSplitSection ur träningsvyns inställningsdialog och ur settings_dialog.py, eftersom andelen nu ställs in direkt i kortet; train_ratio() och TRAIN_RATIO_KEY ligger kvar.
4. Uppdatera testerna som pekade på den gamla dialogen (test_settings_dialog, test_form_width) och lägg till ett test för det nya kortet.
5. Verifiera med sviten.
<!-- SECTION:PLAN:END -->

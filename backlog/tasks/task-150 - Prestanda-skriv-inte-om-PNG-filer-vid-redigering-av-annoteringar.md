---
id: TASK-150
title: 'Prestanda: skriv inte om PNG-filer vid redigering av annoteringar'
status: To Do
assignee: []
created_date: '2026-11-17T20:54:00Z'
labels:
  - performance
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
priority: low
type: enhancement
ordinal: 148000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När ett sparat bildpar redigeras konverteras bilden BGR->QImage->BGR och replace_samples skriver om PNG-filen med cv2.imwrite även fast bara rektanglar/klasser kan ändras (utvärdering_argon.md §5.4). Behåll original-frame i AnnotationCanvas och uppdatera bara .txt-labelfiler och dataset.json vid redigering.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Redigering av befintligt bildpar skriver inte om PNG-filen (mtime oförändrad)
- [ ] #2 Labelfiler och metadata uppdateras korrekt (tester passerar)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

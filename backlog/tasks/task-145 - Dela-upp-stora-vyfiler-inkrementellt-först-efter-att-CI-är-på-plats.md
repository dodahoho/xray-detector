---
id: TASK-145
title: Dela upp stora vyfiler inkrementellt (först efter att CI är på plats)
status: To Do
assignee: []
created_date: '2026-11-17T20:52:00Z'
labels:
  - refactor
  - review-followup
dependencies:
  - TASK-123
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
priority: medium
type: enhancement
ordinal: 143000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
dataset_view.py (1127 rader), detection_view.py (954), annotation_view.py (804) och training_view.py (603) blandar widgets, affärslogik, QSettings och trådhantering (alla tre utvärderingarna). Big-bang-refaktorering är förbjuden innan CI körs: bryt ut EN widget i taget när filen ändå rörs, börja med FlowLayout till ui/flow_layout.py, sedan CaptureCard/Thumbnail och StreamPanel/ResourceMeter.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 FlowLayout ligger i egen modul och dataset_view.py är märkbart mindre
- [ ] #2 Varje utbrytning är en egen liten ändring med passerande tester (ingen big-bang)
- [ ] #3 Ingen vyuppdelning påbörjas innan TASK-123 (CI) är Done
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

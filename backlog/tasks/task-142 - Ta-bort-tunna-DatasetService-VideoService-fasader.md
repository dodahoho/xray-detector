---
id: TASK-142
title: Ta bort tunna DatasetService/VideoService-fasader
status: In Progress
assignee: []
created_date: '2026-11-17T20:52:00Z'
updated_date: '2026-11-18T07:29:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - review_vibe_deepseek41_flash.md
priority: medium
type: enhancement
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DatasetService är 150 rader där 25 av 26 metoder är enradsdelegeringar till DatasetStore; VideoService delegerar 1-till-1 till CameraService (utvärdering_argon.md §4.1, review_vibe_deepseek41_flash.md P2.9). Vid motsägelsen väljs enklaste alternativet med minst kod: ta bort fasaderna och låt vyerna använda DatasetStore/CameraService direkt (alternativet att fasaden äger verklig logik som num_objects/exportlayout får bara väljas om det finns ett konkret behov).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Beslut är genomfört: fasaderna är borttagna eller äger verklig logik
- [ ] #2 ui importerar inte längre tunna pass-through-fasader utan eget syfte
- [ ] #3 Alla tester passerar
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

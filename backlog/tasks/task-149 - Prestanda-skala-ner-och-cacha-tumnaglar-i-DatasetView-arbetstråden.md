---
id: TASK-149
title: 'Prestanda: skala ner och cacha tumnaglar i DatasetView-arbetstråden'
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
ordinal: 147000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DatasetView._load läser varje bild i full upplösning till RAM vid varje refresh (~6-8 GB för 1000 bilder) bara för 170 px tumnaglar, och läser om alla bilder vid varje sparad annotering (utvärdering_argon.md §5.1, endast argon). Skala ner QImage till THUMB_HEIGHT redan i arbetstråden (QImage/QPainter är trådsäkra) och cacha tumnaglar i minnet eller under datasets/.thumbs/ indexerat på (image_id, mtime, annotations).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 1000 bilder i datasetet använder ~150 MB istället för ~8 GB RAM vid visning
- [ ] #2 Refresh efter sparad annotering avkodar bara nya/ändrade bilder (cache träffar)
- [ ] #3 Alla dataset-tester passerar
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

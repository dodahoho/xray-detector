---
id: TASK-64
title: Dataset - Thumbnails med inritade detektioner
status: In Progress
assignee:
  - '@vibe-mistral'
created_date: '2026-11-12T14:22:00Z'
updated_date: '2026-11-12T14:36:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 62000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Det vore önskvärt om de annoterade detektionerna var inritade även i thumbnails för bildparen
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Thumbnailen för en sparad bild visar bildens annoteringar inritade med klassens färg
- [ ] #2 Ramen hamnar över objektets bbox, skalad till thumbnailens storlek
- [ ] #3 En thumbnail utan annoteringar ritas utan ramar
<!-- AC:END -->

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
1. Rita avbildningens annoteringar på thumbnailen med klassfärgen från ui/colors.py, skalat från originalbildens mått till thumbnailens höjd.
2. Låt ritningen ske i GUI-tråden där QPixmap skapas, så arbetstråden fortsätter dekoda QImage.
3. Test: thumbnailens pixmap innehåller klassfärgen när bilden har annoteringar, och inte när den saknar dem.
4. Uppdatera README och verifiera med hela testsviten.
<!-- SECTION:PLAN:END -->

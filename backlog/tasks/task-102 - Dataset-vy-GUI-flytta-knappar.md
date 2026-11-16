---
id: TASK-102
title: Dataset vy - GUI flytta knappar
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-16T20:52:00Z'
updated_date: '2026-11-16T21:01:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 100000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Flytta knapparna för att utöka/återställa dataset till höger sida men ha ett mellanrum till knapparna för att exportera dataset så att utöka/återställ ändå upplevs som en egen knappgrupp
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
1. Lägg en stretch först i datasetvyns knapprad så hela raden hamnar till höger.
2. Lägg Utöka/Återställ först i den högra gruppen och sätt ett fast mellanrum (addSpacing) före exportknapparna, så utöka/återställ upplevs som en egen knappgrupp.
3. Verifiera med sviten (test_shortcuts, test_busy_operations, test_dataset_variation_view).
<!-- SECTION:PLAN:END -->

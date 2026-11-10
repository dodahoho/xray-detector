---
id: TASK-30
title: Titelrad för bildpar i dataset
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T09:06:00Z'
updated_date: '2026-11-10T09:14:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ersätt "Fångst 1", "Fångst 2" osv med datum och tid när bilderna fångades 

YYYY-MM-DD HH:MM:SS
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Rubriken för en fångst visar datum och tid i formatet YYYY-MM-DD HH:MM:SS
- [ ] #2 Tiden är den tidpunkt då bilderna fångades
- [ ] #3 Äldre dataset utan sparad tid faller tillbaka på bildfilens tidsstämpel
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
1. add_samples skriver 'captured' (ISO-tid) på varje bild; tiden kommer från pending-fångstens saved_at när den finns, annars now().
2. PendingCapture får saved_at och pending_saved_at() läser indexet utan att dekoda bilder.
3. Datasetvyn visar tiden som 'YYYY-MM-DD HH:MM:SS' i rubriken i stället för 'Fångst N'; äldre dataset faller tillbaka på bildfilens mtime.
4. Tester: rubriken visar tiden, fallback för äldre dataset, pending visar saved_at.
<!-- SECTION:PLAN:END -->

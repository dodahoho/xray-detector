---
id: TASK-104
title: Träningsvy - knapptext om nattetid eller inaktivitet är vald
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-16T20:56:00Z'
updated_date: '2026-11-16T21:01:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 102000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Om Nattetid eller Schemalägg är valt, byt knapptexten från Starta till Schemalägg
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
1. Koppla run_combo.currentIndexChanged till en uppdatering av startknappens etikett.
2. Etiketten blir 'Sta&rta träning' vid Direkt och '&Schemalägg träning' vid Nattetid/Inaktivitet, så mnemoniken följer texten.
3. Verifiera med sviten (test_shortcuts, test_training_scheduler).
<!-- SECTION:PLAN:END -->

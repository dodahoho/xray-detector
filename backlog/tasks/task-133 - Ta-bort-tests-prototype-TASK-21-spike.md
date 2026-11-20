---
id: TASK-133
title: Ta bort tests/prototype/ (TASK-21-spike)
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:51:00Z'
updated_date: '2026-11-17T22:21:00Z'
labels:
  - cleanup
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - tests/prototype/annotation_scene.py
  - tests/prototype/test_prototype_annotation_scene.py
  - tests/prototype/__init__.py
priority: medium
type: chore
ordinal: 338000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Prototypen körs vid varje pytest-körning trots att den inte testar produktionskod, muterar sys.path globalt och definierar en klass med samma namn som produktionsklassen (alla tre utvärderingarna är överens). Ta bort hela katalogen; kunskapen finns kvar i TASK-21.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/prototype/ är borttagen och pytest samlar inte längre dess 6 tester
- [x] #2 Hela pytest-sviten passerar
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Ta bort hela tests/prototype/ med git rm: annotation_scene.py, test_prototype_annotation_scene.py och __init__.py.

2. Kör hela sviten och kontrollera att antalet insamlade tester minskar med de sex prototyptesterna.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
tests/prototype/ är borttagen med git rm. Katalogen testade en QGraphicsScene-variant som inte används i produktionen, muterade sys.path och definierade en klass med samma namn som produktionsklassen. Kunskapen finns kvar i TASK-21 och docs/decision-annotation-canvas.md.

Verifiering: sviten går från 880 till 874 passed, alltså exakt de sex prototyptesterna färre, och pytest samlar inte längre något från tests/prototype/. Kvar är samma fyra Windows-specifika offscreen-fel som förut. ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
tests/prototype/ är borta. Katalogen testade en QGraphicsScene-prototyp som inte används i produktionen, muterade sys.path globalt och definierade en klass med samma namn som produktionsklassen. Sviten går från 880 till 874 passed, vilket är exakt de sex prototyptesterna, och inga andra tester påverkas. Kunskapen finns kvar i TASK-21 och docs/decision-annotation-canvas.md.
<!-- SECTION:FINAL_SUMMARY:END -->

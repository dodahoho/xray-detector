---
id: TASK-100
title: Ctrl+C visar kraschdialogen Ovantat fel
status: To Do
assignee: []
created_date: '2026-11-16T16:32:00Z'
labels: []
dependencies: []
priority: medium
type: bug
ordinal: 98000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-90. `logs/app.log` innehåller exakt en ERROR-rad, och den är `Ohanterat undantag: ... KeyboardInterrupt`. `install_exception_dialog` i `ui/crash_dialog.py` ersätter `sys.excepthook`, som även anropas för `KeyboardInterrupt`. Att avbryta appen med Ctrl+C i en konsol ger alltså en modal dialog med rubriken Ovantat fel och full traceback, trots att användaren själv bad om att avbryta. Det gör också att den enda ERROR-raden i loggen är ett falsklarm, vilket skymmer verkliga fel vid genomgång av loggen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Ctrl+C avslutar appen utan att visa kraschdialogen
- [ ] #2 Ctrl+C loggas inte som ett ohanterat undantag
- [ ] #3 Ett verkligt ohanterat undantag visar fortfarande dialogen och loggas som ERROR
- [ ] #4 Test täcker att excepthook-kroken hoppar över KeyboardInterrupt
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

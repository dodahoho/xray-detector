---
id: TASK-34
title: Testsviten kraschar ibland med access violation
status: To Do
assignee: []
created_date: '2026-11-10T13:05:00Z'
labels:
  - test
  - robusthet
dependencies: []
references:
  - tests/test_training_worker.py
  - tests/test_resources.py
priority: medium
type: bug
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Den fullständiga testsviten kraschar ibland med 'Windows fatal exception: access violation' och avslutas med exit-kod 139 (segmentation fault). Kraschstället ligger i tests/test_training_worker.py::test_cancel_terminates_long_running_process, i wait_for som anropar qapp.processEvents() — alltså när en köad händelse eller timer från ett tidigare test körs, inte i testet självt.

Observerat 2026-11-10 vid arbete med TASK-33:
- Kraschar cirka 2 av 3 körningar av 'pytest -q' på HEAD före TASK-33:s ändring, så det är inte infört av den.
- Utan tests/test_resources.py: 5 av 5 gröna körningar. Med den: cirka 2 av 3 krascher. Något i den filen, eller dess samverkan med tidigare tester, utlöser kraschen.
- Att stänga av DetectionViews resurstimer (self.resource_timer.start()) ändrade inte frekvensen, så det är inte timern ensam.
- När sviten inte kraschar: 147 passed, 1 skipped.

Konsekvens: gröna körningar är opålitliga och en CI skulle bli flakig. Kraschorsaken är inte utredd.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Hela testsviten (pytest -q) går tio körningar i rad utan krasch eller access violation
- [ ] #2 Orsaken till kraschen är identifierad och dokumenterad i uppgiften
- [ ] #3 Antalet passerande tester är oförändrat eller högre
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

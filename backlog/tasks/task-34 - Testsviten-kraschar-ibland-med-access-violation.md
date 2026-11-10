---
id: TASK-34
title: Testsviten kraschar ibland med access violation
status: Done
assignee: []
created_date: '2026-11-10T13:05:00Z'
updated_date: '2026-11-10T15:16:00Z'
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
- [x] #1 Hela testsviten (pytest -q) går tio körningar i rad utan krasch eller access violation
- [x] #2 Orsaken till kraschen är identifierad och dokumenterad i uppgiften
- [x] #3 Antalet passerande tester är oförändrat eller högre
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rotorsak: flera tester skapar MainWindow och DetectionView som aldrig stängs. De lämnas till garbage collector, som kan köra mitt i ett processEvents()-anrop i ett senare test. Då rivs ett Qt-objekt inuti Qt:s egen händelseloop, vilket ger access violation. Kraschstället blev därför alltid test_training_worker.py::test_cancel_terminates_long_running_process, vars wait_for är den mest intensiva processEvents()-loopen i sviten — inte för att testet i sig är fel.

Bevis: med en autouse-fixture som kör gc.collect() efter varje test gick sviten 10 av 10 grönt. Utan den kraschade cirka 2 av 3 körningar. Att stänga av DetectionViews resurstimer ändrade inte frekvensen nämnvärt (3 av 5 kraschade), så det var inte timern. Att skapa och släppa sex MainWindow i rad med gc.collect() mellan kraschade inte, vilket pekar på att det är rivningen inuti processEvents som är farlig, inte objekten i sig.

Ytterligare bevis: TASK-35:s pacing-ändring gjorde kraschen deterministisk (3 av 3). Med denna fix applicerad går sviten 3 av 3 grönt även med pacing-ändringen, så fixen löser den underliggande livstidsfrågan och inte bara ett symptom.

Åtgärd: autouse-fixture _collect_qt_objects i tests/conftest.py som kör gc.collect() efter varje test. Kostnaden är cirka 4 s på hela sviten (11 s -> 15 s). DoD #4: fixturens docstring dokumenterar varför; ingen användardokumentation påverkas.

Verifiering: 10 av 10 körningar av hela sviten gröna, 147 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Testsviten kraschade för att Qt-objekt revs inuti processEvents(). Flera tester skapar MainWindow och DetectionView som aldrig stängs; garbage collector kunde då riva dem mitt i ett processEvents()-anrop i ett senare test, vilket gav access violation i test_training_worker. En autouse-fixture i tests/conftest.py samlar nu skräpet efter varje test, så objekten rivs på en säker punkt.

Verifierat: 10 av 10 körningar av hela sviten gröna (147 passed, 1 skipped), mot cirka 2 av 3 krascher före. Fixen gör också TASK-35:s pacing-ändring körbar: 3 av 3 grönt med den applicerad, mot 3 av 3 krascher innan.
<!-- SECTION:FINAL_SUMMARY:END -->

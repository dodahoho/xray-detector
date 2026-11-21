---
id: TASK-176
title: >-
  Appen tappar terminalen efter UTF-8-omstarten - kommandoprompten kommer inte
  tillbaka
status: In Progress
assignee: []
created_date: '2026-11-21T00:39:00Z'
updated_date: '2026-11-21T00:39:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/app.py
  - tests/test_utf8_mode.py
  - docs/arkitektur.md
type: bug
ordinal: 468000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Efter TASK-173 startar appen om sig själv med os.execv för att slå på UTF-8-läget. På Windows spawnar os.execv en ny process och avslutar den gamla, så appen blir en föräldralös process som terminalen inte längre väntar på. Kommandoprompten kommer därför inte tillbaka när appen stängs; användaren måste trycka Ctrl+C.

Före TASK-173 körde appen i förgrunden, och processen avslutades när fönstret stängdes. Det syntes också i loggen: sessionen 2026-11-20 23:51 saknar avslutsrad.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Appen stannar kvar i terminalen efter UTF-8-omstarten, så kommandoprompten kommer tillbaka när appen stängs
- [x] #2 UTF-8-läget slås fortfarande på för appen och träningsprocessen
- [x] #3 Alla tester går igenom
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Byt os.execv mot en omstart som väntar på den nya processen, så appen stannar kvar i terminalen.

2. Låt föräldern avsluta med barnets kod och fånga Ctrl+C utan traceback.

3. Uppdatera testerna i test_utf8_mode.py till den nya omstarten.

4. Uppdatera docs/arkitektur.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Orsak: os.execv i _ensure_utf8_mode (TASK-173) spawnar en ny process och avslutar den gamla på Windows. Appen blev därför en föräldralös process som terminalen inte längre väntade på, och kommandoprompten kom inte tillbaka när appen stängdes.

Åtgärd: omstarten görs med subprocess.run, som väntar på den nya processen. Föräldern avslutar med barnets kod och fångar Ctrl+C utan traceback. Appen stannar därmed i terminalen, som före TASK-173, och UTF-8-läget slås fortfarande på eftersom barnet ärver PYTHONUTF8=1 och RESTARTED_ENV.

Verifiering: test_utf8_mode.py har nya tester för kommandoraden, barnets slutkod och att omstarten sker högst en gång. Hela sviten 1045 passed, 1 skipped, ruff check går igenom. Kört appen via cmd /c med en timer som stänger fönstret: kommandot väntar på appen (10 s i stället för 0 s), loggen får 'Avslutar: stänger processen' och inga QThreadStorage-varningar skrivs.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
UTF-8-omstarten använde os.execv, som på Windows lämnar kvar en föräldralös process som terminalen inte längre väntar på. Appen stannade därför inte i terminalen, och kommandoprompten kom inte tillbaka när fönstret stängdes.

Omstarten görs nu med subprocess.run, som väntar på den nya processen. Föräldern avslutar med barnets kod och fångar Ctrl+C utan traceback. Appen stannar i terminalen som före TASK-173, och UTF-8-läget slås fortfarande på eftersom barnet ärver PYTHONUTF8=1.

Verifierat: nya tester i test_utf8_mode.py, hela sviten 1045 passed, 1 skipped, ruff check går igenom, och en körning via cmd /c väntar på appen och avslutas med avslutsraden i loggen.
<!-- SECTION:FINAL_SUMMARY:END -->

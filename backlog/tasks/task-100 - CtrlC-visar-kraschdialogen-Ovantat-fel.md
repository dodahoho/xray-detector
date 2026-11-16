---
id: TASK-100
title: Ctrl+C visar kraschdialogen Ovantat fel
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:32:00Z'
updated_date: '2026-11-16T20:50:00Z'
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
- [x] #1 Ctrl+C avslutar appen utan att visa kraschdialogen
- [x] #2 Ctrl+C loggas inte som ett ohanterat undantag
- [x] #3 Ett verkligt ohanterat undantag visar fortfarande dialogen och loggas som ERROR
- [x] #4 Test täcker att excepthook-kroken hoppar över KeyboardInterrupt
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
1. I ui/crash_dialog.py: låt excepthook_with_dialog hoppa över KeyboardInterrupt innan den loggar eller visar dialog.
2. Vid KeyboardInterrupt: logga INFO 'Avbryter: Ctrl+C' (inte ERROR/ohanterat undantag), stäng QApplication så app.exec() returnerar, och fall tillbaka på sys.__excepthook__ när ingen Qt-app finns.
3. Tester: kroken visar ingen dialog och loggar ingen ERROR för KeyboardInterrupt, ett verkligt undantag visar fortfarande dialogen och loggas som ERROR.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat: excepthook_with_dialog kontrollerar exc_type mot KeyboardInterrupt först och delegerar till _quit_on_interrupt(). Den loggar "Avbryter: Ctrl+C" som INFO, hämtar QApplication.instance() och anropar app.quit() så att app.exec() returnerar. Utan Qt-app tar sys.__excepthook__ över, så en konsolkörning beter sig som vanligt.

Verifierat: 2 nya tester i tests/test_crash_dialog.py. Skarp kontroll med en riktig QApplication: en KeyboardInterrupt i en Qt-callback gav app.exec() = 0, INFO-raden "Avbryter: Ctrl+C" i app.log och noll ERROR-rader, och ingen dialog visades (skriptet hade blockerat i box.exec() annars). Det befintliga testet för ett verkligt undantag visar fortfarande dialog och ERROR.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ctrl+C är nu ett avsiktligt avbrott i stället för en krasch. excepthook-kroken känner igen KeyboardInterrupt innan den loggar eller visar dialog, skriver en INFO-rad och stänger Qt-appen så att app.exec() returnerar. Därmed är den enda ERROR-raden i loggen alltid ett verkligt fel, och användaren slipper en modal dialog med full traceback för något den själv bad om. Utan QApplication faller kroken tillbaka på sys.__excepthook__, så konsolkörningar beter sig som vanligt. Verifierat med 2 nya tester och en skarp körning: app.exec() returnerade 0, INFO loggades, noll ERROR-rader och ingen dialog.
<!-- SECTION:FINAL_SUMMARY:END -->

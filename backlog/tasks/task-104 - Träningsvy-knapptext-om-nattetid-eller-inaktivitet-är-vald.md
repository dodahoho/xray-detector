---
id: TASK-104
title: Träningsvy - knapptext om nattetid eller inaktivitet är vald
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T20:56:00Z'
updated_date: '2026-11-16T21:15:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 196000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Om Nattetid eller Schemalägg är valt, byt knapptexten från Starta till Schemalägg
<!-- SECTION:DESCRIPTION:END -->

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
1. Koppla run_combo.currentIndexChanged till en uppdatering av startknappens etikett.
2. Etiketten blir 'Sta&rta träning' vid Direkt och '&Schemalägg träning' vid Nattetid/Inaktivitet, så mnemoniken följer texten.
3. Verifiera med sviten (test_shortcuts, test_training_scheduler).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
run_combo.currentIndexChanged är kopplad till _update_start_label(), som sätter Sta&rta träning vid Direkt och &Schemalägg träning vid Nattetid och Efter inaktivitet. Mnemoniken följer etiketten, så Alt+R och Alt+S pekar ut samma knapp i det läge den står i. Etiketten sätts också när kortet byggs, så den aldrig står kvar i fel läge.

Nytt test i tests/test_training_scheduler.py låser alla tre lägena.

Verifiering: hela sviten gick igenom (770 passed, 1 skipped) och ruff check på de ändrade filerna gav inga fel.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Startknappen i träningsvyn heter nu Schemalägg träning när Nattetid eller Efter inaktivitet är valt, och Starta träning vid Direkt. Mnemoniken följer etiketten (Alt+R respektive Alt+S), så genvägen pekar ut samma knapp i det läge den står i.

Verifiering: hela sviten gick igenom (770 passed, 1 skipped) med ett nytt test som låser alla tre lägena, och ruff check på de ändrade filerna gav inga fel.
<!-- SECTION:FINAL_SUMMARY:END -->

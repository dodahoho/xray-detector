---
id: TASK-77
title: Detektion - Toggle knapp för markera alla/avmarkera alla
status: Done
assignee: []
created_date: '2026-11-12T21:06:00Z'
updated_date: '2026-11-12T21:20:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/settings_dialog.py
  - tests/test_class_filter.py
  - README.md
type: enhancement
ordinal: 75000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
I inställngarna för detektionsvyn kan man välja vilka objektklasser som ska detekeras. Där bör det finnas en knapp för att snabbt markera alla / avmarkera alla (toggle).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Klassfiltret i detektionsvyns inställningar har en knapp som markerar alla klasser
- [x] #2 Knappen avmarkerar alla klasser när alla redan är markerade
- [x] #3 Knappens etikett visar vad nästa klick gör
- [x] #4 Ändringen sparas och filtrerar detektionen direkt, med ett anrop till vyn
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
1. Lägg till en toggle-knapp i ClassFilterSection ovanför klasslistan.
2. Knappen markerar alla klasser när någon är avmarkerad, annars avmarkerar den alla.
3. Etiketten följer läget: "Markera alla" / "Avmarkera alla", med mnemonik.
4. Blockera kryssrutornas signaler under omslaget så on_changed anropas en gång, inte en gång per klass.
5. Uppdatera varningen och knapptexten när enskilda kryssrutor ändras.
6. Tester i test_class_filter.py.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ClassFilterSection har fått en knapp ovanför klasslistan. Den markerar alla klasser när någon är avmarkerad och avmarkerar alla när alla är markerade, så ett klick alltid gör det som återstår.

Kryssrutornas signaler blockeras under omslaget och on_changed anropas en gång med hela listan, så vyn sparar inställningen och startar om detektionen en gång i stället för en gång per klass.

Etiketten följer läget (Markera alla / Avmarkera alla) och har mnemonik Alt+M i båda lägena. Varningen för inga valda klasser uppdateras av samma väg som vid ett enskilt klick.

Verifiering: 516 passed, 1 skipped. Nya tester i test_class_filter.py: markera alla, avmarkera alla, ett anrop till vyn, etiketten i båda lägena, etiketten följer en enskild kryssruta, varningen, samt två vynivåtester som kontrollerar sparat val och att detektionen kopplas bort respektive startas om en gång. Dialogrutan renderades också och knappen syns ovanför listan med rätt etikett i båda lägena.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Klassfiltret i detektionsvyns inställningar har en knapp ovanför klasslistan som växlar mellan alla och inga klasser. Den markerar alla när någon är avmarkerad och avmarkerar alla när alla är markerade, och etiketten visar vad nästa klick gör. Kryssrutornas signaler blockeras under omslaget, så vyn får ett enda besked och detektionen startas om en gång i stället för en gång per klass. Verifierat med 516 passerande tester, inklusive vynivåtester för sparat val och omstart, och en renderad dialog som visar knappen i båda lägena.
<!-- SECTION:FINAL_SUMMARY:END -->

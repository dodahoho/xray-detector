---
id: TASK-87
title: >-
  Träning - Förtydliga bildstorlekens label (längsta sidan,
  horisontell/vertikal)
status: Done
assignee: []
created_date: '2026-11-16T14:14:00Z'
updated_date: '2026-11-16T14:23:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/training_view.py
  - xray_detector/application/training_history.py
  - tests/test_training_history.py
  - tests/test_training_imgsz.py
  - README.md
type: enhancement
ordinal: 381000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Fältet 'Bildstorlek' i träningsvyn visar ett enskilt tal (t.ex. 640) utan att säga om det avser bildens horisontella eller vertikala sida. Ultralytics letterboxar bilden till en kvadrat på imgsz x imgsz pixlar, och appen härleder defaulten ur datasetets längsta sida (imgsz_for i domain/training.py), så 1280x720 ger 1280 och inte 720. Labeln behöver säga det, annars är det lätt att ange den korta sidan och få en modell som skalar ned bilden i onödan.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Labeln i träningsvyn anger att värdet är bildens längsta sida
- [x] #2 En tooltip på bildstorleksfältet förklarar att bilden skalas till en kvadrat imgsz x imgsz och att 1280x720 ger 1280 (horisontell) medan 720x1280 ger 1280 (vertikal)
- [x] #3 Raden i Tidigare träningar använder samma formulering som inställningen
- [x] #4 README beskriver att värdet är den längsta sidan
- [x] #5 Testerna verifierar den nya labeln och tooltipen
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
1. Byt labeln i ui/training_view.py till att namnge den längsta sidan och lägg en tooltip som förklarar kvadraten och horisontell/vertikal.
2. Använd samma formulering i detaljraden i application/training_history.py.
3. Uppdatera README:s träningsavsnitt.
4. Uppdatera test_training_history.py och lägg till label-/tooltip-verifiering i test_training_imgsz.py.
5. Kör testsviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Labeln är nu 'Bildstorlek (längsta sidan):' med en tooltip som förklarar att ultralytics skalar till en kvadrat imgsz x imgsz, så 1280x720 ger 1280 (horisontell) och 720x1280 ger 1280 (vertikal). Samma formulering används i detaljraden för en tidigare träning. Verifierat: tests/test_training_imgsz.py, tests/test_training_history.py och tests/test_form_width.py ger 43 passed. Ruff rapporterar inga nya fel (I001/F401 i training_view.py fanns redan på HEAD).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fältet i träningsvyn heter nu 'Bildstorlek (längsta sidan)' och har en tooltip som förklarar att ultralytics skalar bilden till en kvadrat på Bildstorlek x Bildstorlek px, så 1280x720 ger 1280 (horisontell) och 720x1280 ger 1280 (vertikal). Detaljraden för en tidigare träning använder samma formulering, och README:s träningsavsnitt förklarar varför värdet är den längsta sidan. Verifiering: tests/test_training_imgsz.py::test_imgsz_label_and_tooltip_name_the_longest_side läser labeln via QFormLayout.labelForField och båda tooltip-exemplen; tests/test_training_history.py kontrollerar den nya detaljraden. 43 tester i test_training_imgsz/test_training_history/test_form_width passerar, liksom resten av sviten (448 tester i fullkörningen fram till 72 procent plus samtliga återstående filer i batchar). En enstaka flakig körning föll på test_shortcuts.py::test_alt_letter_switches_tab, som passerar både enskilt och i grupp och inte rör bildstorleken. Ruff: inga nya fel (I001/F401 i training_view.py fanns redan på HEAD).
<!-- SECTION:FINAL_SUMMARY:END -->

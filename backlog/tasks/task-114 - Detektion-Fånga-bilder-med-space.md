---
id: TASK-114
title: Detektion - Fånga bilder med space
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T11:57:00Z'
updated_date: '2026-11-17T12:14:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/detection_view.py
  - tests/test_shortcuts.py
  - README.md
type: enhancement
ordinal: 112000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Space-tangenten ska vara kopplad till knappen Fånga
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Space-tangenten utlöser samma fångst som knappen Fånga bilder
- [x] #2 Genvägen syns i knappens etikett enligt projektets konvention
- [x] #3 Genvägen utlöses bara när detektionsvyn är aktiv
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
1. Bind Space som WindowShortcut på DetectionView till samma slot som knappen (_on_capture), via bind_shortcut i ui/shortcuts.py.
2. Visa genvägen i etiketten med with_hint ovanpå mnemonic, så konventionen 'genvägar som inte är mnemonik visas inom parentes' hålls.
3. Uppdatera test_shortcuts.py (etikett och mängden genvägar) och lägg till ett test som trycker Space och får en fångst.
4. Uppdatera README:s tabell över tangentbordsgenvägar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Space binds med bind_shortcut (WindowShortcut på DetectionView) till samma slot som knappen, så genvägen bara utlöses när detektionsvyn är den aktiva fliken. Etiketten blev '&Fånga bilder (Space)' enligt konventionen att genvägar som inte är mnemonik visas inom parentes.

Verifiering: tests/test_shortcuts.py — test_space_captures_like_the_button (Space ger 'Ingen videokälla att fånga ifrån' utan källa), test_space_does_not_fire_on_inactive_tab (ingen fångst från Dataset-fliken), test_button_labels_show_underline_or_hint och test_shortcuts_do_not_collide_with_the_canvas uppdaterade. Hela sviten: 829 passed, 1 skipped.

Känd avvägning: Space tar över QComboBox standardtangent i detektionsvyn, så modellväljarens dropdown öppnas med Alt+Down eller F4 i stället. QDoubleSpinBox behåller Space.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Space utlöser nu samma fångst som knappen Fånga bilder. Genvägen binds som WindowShortcut på detektionsvyn, så den bara är aktiv när fliken är öppen, och etiketten visar '(Space)' enligt projektets konvention. README:s genvägstabell är uppdaterad. Verifierat med tre nya eller uppdaterade tester i tests/test_shortcuts.py och hela sviten (829 passed, 1 skipped). Avvägning: modellväljarens dropdown öppnas med Alt+Down/F4 i stället för Space.
<!-- SECTION:FINAL_SUMMARY:END -->

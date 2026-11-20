---
id: TASK-114
title: Detektion - Fånga bilder med space
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T11:57:00Z'
updated_date: '2026-11-17T12:51:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/detection_view.py
  - tests/test_shortcuts.py
  - README.md
type: enhancement
ordinal: 354000
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

Space vinner också över vyens inmatningsfält: _CaptureKeyFilter avvisar ShortcutOverride för Space på de fält som kan ta fokus. Fältet QDoubleSpinBox accepterar annars tangenten eftersom tecknet kan skrivas in, och då hinner genvägen aldrig utlösas. Knappar och QComboBox släpper redan igenom Space till genvägen, så filtret behövs bara för textfälten. Filtret sitter på fälten i stället för på applikationen: ett applikationsfilter går igenom Python för varje händelse i hela appen och gjorde testsviten cirka 50 procent långsammare.

Verifiering: tests/test_shortcuts.py — test_space_captures_like_the_button, test_space_captures_while_the_threshold_field_has_focus, test_space_captures_while_a_button_has_focus (knappen aktiveras inte), test_space_does_not_fire_on_inactive_tab, samt uppdaterade test_button_labels_show_underline_or_hint och test_shortcuts_do_not_collide_with_the_canvas. Hela sviten: 831 passed, 1 skipped, 207 s (samma tid som före ändringen).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Space utlöser nu samma fångst som knappen Fånga bilder, oavsett vilket fält i detektionsvyn som har fokus. Genvägen binds som WindowShortcut på vyn, så den bara är aktiv när fliken är öppen, och etiketten visar '(Space)' enligt projektets konvention. Ett litet filter på vyens fält avvisar fältens ShortcutOverride för Space, så tröskelfältet inte tar över tangenten; knappar och modellväljaren släppte redan igenom den. README:s genvägstabell och avsnittet om WindowShortcut är uppdaterade. Verifierat med fem tester i tests/test_shortcuts.py och hela sviten (831 passed, 1 skipped, 207 s).
<!-- SECTION:FINAL_SUMMARY:END -->

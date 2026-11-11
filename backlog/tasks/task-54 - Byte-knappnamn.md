---
id: TASK-54
title: Byte knappnamn
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T19:35:00Z'
updated_date: '2026-11-11T19:42:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 52000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Byt namn på knappar "Vyns inställningar" till "Inställningar" och ge den en lämplig keyboard shortcut. Det är troligtvis vanligare att man nyttjar inställningar för respektive vy än de globala inställningarna via dedikerade fliken Inställningar så shortcut "I" kan kopplas till inställningar i vyerna och så får globala inställningarna (fliken) en annan.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Knapparna i vyerna heter "Inställningar" och nås med Alt+I
- [x] #2 Fliken Inställningar har en egen genväg (Alt+L) som inte krockar med vyernas mnemonik
- [x] #3 Alt+I öppnar den aktiva vyns inställningar i stället för att byta flik
- [x] #4 README och groma-arkitekturen beskriver de nya genvägarna
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
1. settings_dialog.py: knapptexten blir mnemonic("Inställningar", "I") = "&Inställningar" (Alt+I) i stället för "&Vyns inställningar" (Alt+V).
2. main_window.py: fliken Inställningar får Alt+L ("Instä&llningar") eftersom Alt+I nu ägs av vyernas inställningsknappar och mnemoniken måste vara unik mellan flikraden och synliga knappar.
3. Tester: test_shortcuts.py (flikrad, knappetiketter, registrerade genvägar), test_settings_dialog.py (knapptext, fliktext) och test_gui_smoke.py (fliktext).
4. README: genvägstabellen och texten om inställningsknappen.
5. groma: settings-dialog.md och main-window.md uppdateras via groma edit.
6. Verifiering: hela testsviten, ruff på ändrade filer samt visuell granskning av flikrad och knappar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
settings_button() bygger nu knappen mnemonic("Inställningar", "I") = "&Inställningar" (Alt+I) i stället för "&Vyns inställningar" (Alt+V). Fliken Inställningar får Alt+L ("Instä&llningar") i main_window.py, eftersom Alt+I nu ägs av vyernas inställningsknappar och test_mnemonics_are_unique_per_view kräver att flikradens bokstäver är unika och skilda från synliga knappar. L är den enda lediga bokstaven i "Inställningar" förutom Ä; valet av Alt+L framför Alt+Ä och Ctrl+, gjordes av användaren.

Ny test: test_alt_letter_opens_the_view_settings i tests/test_shortcuts.py klickar Alt+I på träningsfliken och verifierar att träningsvyns dialog öppnas och att fliken inte byts. Uppdaterade tester: test_shortcuts.py (flikrad, Alt+L, Alt+I för de fyra knapparna), test_settings_dialog.py (knapptext, fliktext, genväg) och test_gui_smoke.py (fliktext).

Verifiering: hela sviten 242 passed, 1 skipped (40,8 s före ändringen: 241 passed, 1 skipped). ruff är rent på de ändrade raderna; det enda fyndet i de berörda filerna är den befintliga F401 på numpy i test_gui_smoke.py. Flikraden och knapparna är granskade visuellt via QWidget.grab(): fliken visar "Inställningar" med l understruket, knappen visar kugghjulet och "Inställningar" med I understruket, och den avstängda varianten är nedtonad som förut.

Modified files: xray_detector/ui/settings_dialog.py, xray_detector/ui/main_window.py, tests/test_shortcuts.py, tests/test_settings_dialog.py, tests/test_gui_smoke.py, README.md, groma/systems/xray-detector/containers/gui-app/components/settings-dialog.md, groma/systems/xray-detector/containers/gui-app/components/main-window.md
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Vyernas inställningsknapp heter nu **Inställningar** och nås med Alt+I i stället för "Vyns inställningar" (Alt+V). Fliken Inställningar har fått Alt+L ("Instä&llningar"), eftersom Alt+I nu hör till knapparna och mnemoniken måste vara unik mellan flikraden och de synliga knapparna. Det gör att den vanligaste genvägen, inställningarna för vyn man arbetar i, ligger på I och de globala inställningarna på L.

Ändringar: settings_button() i xray_detector/ui/settings_dialog.py bygger knappen med mnemonic("Inställningar", "I"); main_window.py ger inställningsfliken mnemonic("Inställningar", "L"). Testerna i test_shortcuts.py, test_settings_dialog.py och test_gui_smoke.py är uppdaterade, och en ny test (test_alt_letter_opens_the_view_settings) verifierar att Alt+I öppnar träningsvyns dialog och att fliken inte byts. README:s genvägstabell och groma-arkitekturen (settings-dialog.md, main-window.md) beskriver de nya genvägarna.

Verifiering: hela sviten 242 passed, 1 skipped (241 passed, 1 skipped före ändringen). ruff är rent på de ändrade raderna. Flikraden och knapparna är granskade visuellt via QWidget.grab().

Avvägning: Alt+L understryker ett l mitt i ordet. Alternativen var Alt+Ä ("Inst&ällningar") och Ctrl+, utan mnemonik; Alt+L valdes av användaren för att behålla mnemoniksystemet.
<!-- SECTION:FINAL_SUMMARY:END -->

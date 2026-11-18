---
id: TASK-156
title: Globala inställningar flyttas från egen tab
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-18T11:54:00Z'
updated_date: '2026-11-18T12:05:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/theme.py
  - xray_detector/ui/theme_toggle.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/main_window.py
  - xray_detector/ui/settings_dialog.py
  - xray_detector/ui/model_settings.py
  - xray_detector/ui/settings_view.py
  - tests/test_settings_dialog.py
  - tests/test_form_width.py
  - tests/test_gui_smoke.py
  - tests/test_model_settings.py
  - tests/test_annotation_ux.py
  - tests/test_style.py
  - tests/test_shortcuts.py
  - tests/test_detection_toggle.py
  - docs/beteende.md
  - docs/arkitektur.md
  - groma/systems/xray-detector/containers/gui-app/components/theme-toggle.md
  - groma/systems/xray-detector/containers/gui-app/components/settings-view.md
  - groma/systems/xray-detector/containers/gui-app/components/settings-dialog.md
  - groma/systems/xray-detector/containers/gui-app/components/settings-theme.md
  - groma/systems/xray-detector/containers/gui-app/components/model-settings.md
  - groma/systems/xray-detector/containers/gui-app/components/main-window.md
type: enhancement
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Flytta globala inställningen tema (ljus/mörkt) att vara en toggle ikon till höger om knappen inställningar i varje vy. Vid mörkt läge visas en gråskaleikon av en sol (för att ändra till ljust tema) och vid ljust läge visas en gråskaleikon av en måne (för att ändra till mörkt tema)

Den andra delen av de globala inställningarna som rör modeller flyttas till vy detektion och öppnas som en dialog när man trycker på knapp "Hantera modeller" som läggs till höger om modellväljaren. Lägg även lite space till intällning av tröskel på samma rad. Även space mellan tröskel och texten om enhet. Samt lite space mellan enhet och staplarna för gpu/vram/cpu/ram
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. theme.py: is_dark(), toggle_theme() och en gemensam theme_changed-signal.
2. Ny ui/theme_toggle.py: ThemeToggle med grå sol i mörkt läge och grå måne i ljust läge; knappen uppdaterar sig via signalen.
3. Lägg ThemeToggle till höger om inställningsknappen i detektions-, annoterings-, dataset- och träningsvyn.
4. Detektionsvyn: Hantera modeller-knapp till höger om modellväljaren som öppnar ModelSection i en dialog, models_changed-signal, samt spacing före tröskel, mellan tröskel och enhet och mellan enhet och staplarna.
5. MainWindow: ta bort inställningsfliken och SettingsView, koppla detektionsvyns modelländringar till träningsvyn och ge modelldialogen träningsvyns active_run_dir.
6. Ta bort settings_view.py och ThemeSection; uppdatera moduldocstrings.
7. Uppdatera testerna (settings_dialog, form_width, gui_smoke, model_settings, annotation_ux, style, shortcuts) och dokumentationen (docs/beteende.md, groma).
8. Kör ruff och hela sviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Temat växlas nu med ThemeToggle i varje vys överkant: grå sol i mörkt läge, grå måne i ljust, och en gemensam theme_changed-signal gör att alla knappar byter ikon samtidigt. Inställningsfliken är borta; SettingsView och ThemeSection är borttagna. Modellistan ligger i en dialog som öppnas med Hantera modeller (Alt+H) till höger om modellväljaren, och träningsvyns active_run_dir kopplas in så en pågående träning inte kan tas bort. Detektionsvyns översta rad har fått luft före tröskeln, mellan tröskeln och enheten och mellan enheten och resursstaplarna. Testerna är uppdaterade och hela sviten ger 893 passed, 4 failed, där de fyra felen är desamma som på HEAD.
<!-- SECTION:NOTES:END -->

---
id: TASK-43
title: Inställningsknapp per flik i stället för inställningsflik
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T11:30:00Z'
updated_date: '2026-11-11T14:22:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/main_window.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/settings_dialog.py
modified_files:
  - xray_detector/ui/settings_dialog.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/main_window.py
  - xray_detector/ui/settings_view.py
  - tests/test_settings_dialog.py
  - tests/test_shortcuts.py
  - tests/test_gui_smoke.py
  - tests/test_busy_operations.py
  - tests/test_dataset_header.py
  - tests/test_dataset_selection.py
  - tests/test_detection_toggle.py
  - README.md
  - groma/systems/xray-detector/containers/gui-app/components/settings-dialog.md
  - groma/systems/xray-detector/containers/gui-app/components/settings-theme.md
  - groma/systems/xray-detector/containers/gui-app/components/main-window.md
  - groma/systems/xray-detector/containers/gui-app/components/detection-view.md
  - groma/systems/xray-detector/containers/gui-app/components/annotation-view.md
  - groma/systems/xray-detector/containers/gui-app/components/dataset-view.md
  - groma/systems/xray-detector/containers/gui-app/components/training-view.md
  - groma/systems/xray-detector/containers/gui-app/container.md
priority: medium
type: enhancement
ordinal: 41000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Inställningsfliken innehåller i dag bara två grupper: Utseende (tema) och Träningsschema (nattfönster och inaktivitet innan träning). Träningsschemat hör till träningsvyn och temat är globalt. Samtidigt ligger de flesta inställningar redan i respektive flik: detektionsvyn har modell, tröskel, källa och format; annoteringsvyn har klass; datasetvyn har version; träningsvyn har basmodell, datasetversion, epoker, bildstorlek, batch och körläge.

Inställningsfliken blir därför en flik man måste lämna den vy man arbetar i för att nå, trots att det bara är träningsschemat som saknas i sin egen vy.

Önskad struktur: inställningsfliken tas bort och varje flik får en inställningsknapp som öppnar de inställningar som hör till den fliken. Träningsschemat flyttar till träningsvyns inställningar.

Att ta ställning till: temat gäller hela appen, inte en flik. Det kan antingen ligga i en global inställningsknapp utanför flikarna eller i en gemensam sektion i varje fliks dialog. Lösningen ska göra valet tydligt.

Att bevara: nycklarna ui/theme, training/night_start_hour, training/night_end_hour och training/inactivity_minutes ska fortsätta läsas och skrivas, så befintliga användarinställningar inte tappas. Inställningsknappen bör följa genvägskonventionen i TASK-41.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Inställningsfliken är borta och flikraden har fyra flikar
- [x] #2 Varje flik har en inställningsknapp som öppnar de inställningar som hör till fliken
- [x] #3 Träningsschemat (nattfönster och inaktivitet) nås från träningsvyns inställningar
- [x] #4 Temat går fortfarande att byta efter att inställningsfliken tagits bort
- [x] #5 Befintliga sparade värden (ui/theme, training/night_start_hour, training/night_end_hour, training/inactivity_minutes) läses och skrivs som förut
- [x] #6 Inställningsdialogen kan stängas utan att något ändras
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
1. Ny modul xray_detector/ui/settings_dialog.py: ThemeSection (globalt tema), TrainingScheduleSection (nattfönster + inaktivitet), SettingsDialog (titel + sektioner + Stäng) och settings_button() som bygger knappen och öppnar dialogen.
2. Ta bort SettingsView och inställningsfliken; MainWindow bygger fyra flikar.
3. Varje vy får en inställningsknapp (&Inställningar, Alt+I) sist i sin åtgärdsrad som öppnar vyens dialog: träningsvyn får Träningsschema + Utseende, övriga får Utseende.
4. DatasetView tar emot settings så dess dialog kan spara temat.
5. Tester: uppdatera test_gui_smoke, test_shortcuts, test_busy_operations, dataset-testerna och test_detection_toggle; ny tests/test_settings_dialog.py som verifierar AC 1-6.
6. Uppdatera README och groma-arkitekturen.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Inställningsfliken är borta: MainWindow bygger fyra flikar och settings_view.py är raderad. Varje vy äger sin knapp via settings_button() i ui/settings_dialog.py, som också håller sektionerna ThemeSection och TrainingScheduleSection.

Temat ligger i sektionen "Utseende (gäller hela appen)" i varje fliks dialog, så det går att byta från vilken flik som helst utan att det ser ut som en flikinställning. Träningsvyns dialog har dessutom träningsschemat; de andra vyerna har allt sitt inställningsbart direkt i vyn och deras dialog innehåller därför bara temat.

settings_button() är en fabriksfunktion i stället för en QPushButton-subklass: en Python-subklass av QWidget som föräldras av vyn kraschade i gc.collect() i testsviten (access violation i shiboken när C++-föräldern rivit barnet). Samma beteende gick inte att återskapa med en vanlig QPushButton.

DatasetView tar nu emot settings (required) eftersom dess dialog sparar temat; dataset-, header- och busy-testerna skickar in sin QSettings-fixture.

Verifiering: 230 passed, 1 skipped (hela sviten, tre körningar i rad). Nya tests/test_settings_dialog.py täcker AC 1-6. ruff är rent på de nya filerna; de 63 befintliga ruff-felen i repot är oförändrade. Dialogerna och flikraden är också granskade visuellt via QWidget.grab() i en skriptkörning.

Känd avvägning: detektionsvyns rubrikrad är redan bred (1392 px minimum) och inställningsknappen lägger till 87 px. Raden går ihop på maximerat fönster men klipps på smala skärmar, precis som före ändringen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Inställningsfliken är borta. Flikraden har fyra flikar och varje vy har en Inställningar-knapp (Alt+I) sist i sin åtgärdsrad som öppnar de inställningar som hör till vyn.

Ny modul ui/settings_dialog.py: ThemeSection (tema), TrainingScheduleSection (nattfönster och inaktivitet), SettingsDialog (sektioner + Stäng) och settings_button(). Träningsschemat nås nu från träningsvyns dialog. Temat gäller hela appen och ligger i sektionen "Utseende (gäller hela appen)" i varje fliks dialog, så det går att byta från vilken flik som helst utan att det ser ut som en flikinställning. settings_view.py är raderad och DatasetView tar emot settings för att kunna spara temat.

Nycklarna ui/theme, training/night_start_hour, training/night_end_hour och training/inactivity_minutes läses och skrivs som förut, så sparade val från den gamla fliken fortsätter att gälla. Ändringar sparas direkt och Stäng (eller Esc) lämnar allt orört.

Verifiering: hela sviten 230 passed, 1 skipped (tre körningar i rad). tests/test_settings_dialog.py täcker AC 1-6; test_shortcuts, test_gui_smoke, test_detection_toggle, test_busy_operations och dataset-testerna är uppdaterade. ruff är rent på de nya filerna. Dialogerna och flikraden är granskade visuellt via QWidget.grab().

Risker: settings_button() är en fabriksfunktion i stället för en QPushButton-subklass, eftersom subklassen kraschade i gc.collect() i testsviten. Detektionsvyns rubrikrad är redan bred och inställningsknappen lägger till 87 px; raden går ihop maximerat men klipps på smala skärmar, som före ändringen.
<!-- SECTION:FINAL_SUMMARY:END -->

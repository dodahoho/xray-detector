---
id: TASK-43
title: Inställningsknapp per flik i stället för inställningsflik
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T11:30:00Z'
updated_date: '2026-11-11T15:15:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/main_window.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/settings_dialog.py
modified_files:
  - groma/systems/xray-detector/containers/gui-app/components/settings-view.md
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

## Reviderat beslut

Första implementationen tog bort inställningsfliken och lade temat i en gemensam sektion i varje fliks dialog. Det blev inte bra: globala inställningar som mörkt/ljust tema ska inte ligga under en enskild vys inställningar.

- Inställningsfliken finns kvar och håller applikationens globala inställningar, det vill säga sådant som inte hör till någon av de övriga flikarna. I dag är det temat.
- Flikarna Detektion, Annotation, Dataset och Träning har varje en inställningsknapp med en kugghjulsikon före texten.
- Har vyn inga egna inställningar ligger knappen kvar men är avstängd, så placeringen är densamma oavsett vilken flik som är öppen.
- Inställningsknappen sitter på samma ställe i alla vyer: högst upp till höger.
- Träningsschemat ligger kvar i träningsvyns inställningar.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Inställningsfliken finns kvar och håller applikationens globala inställningar (temat)
- [x] #2 Flikraden har fem flikar
- [x] #3 Varje vy har en inställningsknapp med kugghjulsikon före texten
- [x] #4 Inställningsknappen sitter högst upp till höger i alla fyra vyer
- [x] #5 En vy utan egna inställningar har kvar knappen men avstängd
- [x] #6 Träningsschemat (nattfönster och inaktivitet) nås från träningsvyns inställningar
- [x] #7 Temat går att byta från inställningsfliken
- [x] #8 Befintliga sparade värden (ui/theme, training/night_start_hour, training/night_end_hour, training/inactivity_minutes) läses och skrivs som förut
- [x] #9 Inställningsdialogen kan stängas utan att något ändras
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
1. xray_detector/ui/settings_dialog.py håller de återanvändbara delarna: ThemeSection (globalt tema), TrainingScheduleSection (nattfönster + inaktivitet), SettingsDialog (titel + sektioner + Stäng), gear_icon() som ritar en monokrom kugghjulsikon med QPainter och settings_button(parent, title, sections=None) som bygger vyens knapp och öppnar dialogen.
2. xray_detector/ui/settings_view.py återinförs som inställningsflik och visar applikationens globala inställningar genom att komponera ThemeSection.
3. MainWindow bygger fem flikar igen och skapar SettingsView(self.settings); DatasetView tar emot settings så att vyerna delar samma QSettings.
4. Varje vy får en inställningsknapp sist i sin översta rad, alltså högst upp till höger: träningsvyn med TrainingScheduleSection (aktiverad), detektions-, annoterings- och datasetvyn utan egna sektioner (avstängd med tooltip). Träningsvyn får en egen rubrikrad så knappen hamnar på samma plats som i de andra vyerna.
5. Knapptexten är "&Vyns inställningar" (Alt+V) eftersom flikens Alt+I redan är upptagen och test_mnemonics_are_unique_per_view kräver unika mnemonik per vy.
6. Tester: tests/test_settings_dialog.py verifierar AC 1-9; test_shortcuts, test_gui_smoke, test_busy_operations, dataset-testerna och test_detection_toggle uppdateras för fem flikar, ny knappplacering och settings-parametern.
7. README och groma-arkitekturen uppdateras.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Inställningsfliken är borta: MainWindow bygger fyra flikar och settings_view.py är raderad. Varje vy äger sin knapp via settings_button() i ui/settings_dialog.py, som också håller sektionerna ThemeSection och TrainingScheduleSection.

Temat ligger i sektionen "Utseende (gäller hela appen)" i varje fliks dialog, så det går att byta från vilken flik som helst utan att det ser ut som en flikinställning. Träningsvyns dialog har dessutom träningsschemat; de andra vyerna har allt sitt inställningsbart direkt i vyn och deras dialog innehåller därför bara temat.

settings_button() är en fabriksfunktion i stället för en QPushButton-subklass: en Python-subklass av QWidget som föräldras av vyn kraschade i gc.collect() i testsviten (access violation i shiboken när C++-föräldern rivit barnet). Samma beteende gick inte att återskapa med en vanlig QPushButton.

DatasetView tar nu emot settings (required) eftersom dess dialog sparar temat; dataset-, header- och busy-testerna skickar in sin QSettings-fixture.

Verifiering: 230 passed, 1 skipped (hela sviten, tre körningar i rad). Nya tests/test_settings_dialog.py täcker AC 1-6. ruff är rent på de nya filerna; de 63 befintliga ruff-felen i repot är oförändrade. Dialogerna och flikraden är också granskade visuellt via QWidget.grab() i en skriptkörning.

Känd avvägning: detektionsvyns rubrikrad är redan bred (1392 px minimum) och inställningsknappen lägger till 87 px. Raden går ihop på maximerat fönster men klipps på smala skärmar, precis som före ändringen.

Revidering: inställningsfliken återinförs för applikationens globala inställningar (temat). Temat flyttas därför bort från vyernas dialoger, som i stället bara visar vyens egna inställningar. Vyer utan egna inställningar behåller knappen men avstängd, och knappen sitter högst upp till höger i alla vyer.

Revidering enligt användarens beslut: inställningsfliken finns kvar och håller applikationens globala inställningar (i dag temat). Temat flyttas därför bort från vyernas dialoger, som i stället bara visar vyens egna inställningar. settings_view.py är återinförd och komponerar ThemeSection från settings_dialog.py, så den redan upptecknade relationen settings_view.py -> settings_dialog.py stämmer fortfarande.

Inställningsknappen har en kugghjulsikon före texten. Ikonen ritas med QPainter i gear_icon() i stället för att använda Unicode-tecknet U+2699: tecknet renderades som en lila emoji i Windows-temat, medan den ritade ikonen är monokrom (#8a8a8a) och fungerar i både ljust och mörkt tema. Qt dimmar den automatiskt när knappen är avstängd.

Knapptexten är "&Vyns inställningar" (Alt+V) i stället för "&Inställningar" (Alt+I): fliken Inställningar äger redan Alt+I och test_mnemonics_are_unique_per_view kräver unika mnemonik per vy.

settings_button(parent, title, sections=None) är en fabriksfunktion, inte en QPushButton-subklass. En Python-subklass av QWidget som föräldras av vyn kraschade i gc.collect() i testsviten (access violation i shiboken när C++-föräldern rivit barnet). Med sections=None blir knappen avstängd med tooltipen "Vyn har inga egna inställningar", så placeringen är densamma oavsett flik.

Träningsvyn fick en egen rubrikrad (_build_header) med stretch + knapp, så knappen hamnar högst upp till höger som i de tre andra vyerna i stället för i åtgärdsraden längst ned.

Verifiering efter revideringen: 233 passed, 1 skipped i hela sviten (python -m pytest -q, 29,6 s). tests/test_settings_dialog.py har tio tester som täcker AC 1-9. ruff är rent på de ändrade filerna; de 63 befintliga ruff-felen i repot är oförändrade. Flikraden, de fyra vyernas knappar (avstängda respektive aktiverad) och inställningsfliken är granskade visuellt via QWidget.grab().
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Inställningsfliken finns kvar och håller applikationens globala inställningar, det vill säga sådant som inte hör till någon av de övriga flikarna. I dag är det temat, som flyttats tillbaka dit från vyernas dialoger.

Flikarna Detektion, Annotation, Dataset och Träning har varje en inställningsknapp med kugghjulsikon före texten, placerad sist i vyens översta rad och därmed högst upp till höger oavsett vilken flik som är öppen. Träningsvyns knapp öppnar träningsschemat (nattfönster och inaktivitet); de tre andra vyerna har inga egna inställningar och behåller därför knappen avstängd med tooltipen "Vyn har inga egna inställningar".

Ändringar: settings_dialog.py håller ThemeSection, TrainingScheduleSection, SettingsDialog, gear_icon() och settings_button(); settings_view.py är återinförd och komponerar ThemeSection; main_window.py bygger fem flikar igen; de fyra vyerna anropar settings_button() och träningsvyn har fått en egen rubrikrad. README och groma-arkitekturen är uppdaterade.

Två avväganden värda att känna till: kugghjulet ritas med QPainter i stället för Unicode-tecknet U+2699, som renderades som en lila emoji i Windows-temat; och knapptexten är "&Vyns inställningar" (Alt+V) eftersom fliken Inställningar redan äger Alt+I och mnemoniken måste vara unik per vy.

Verifiering: 233 passed, 1 skipped i hela sviten (python -m pytest -q). tests/test_settings_dialog.py har tio tester som täcker AC 1-9, test_shortcuts och test_gui_smoke täcker flikraden och genvägarna, och test_detection_toggle verifierar att knappen ligger sist i rubrikraden. ruff är rent på de ändrade filerna; de 63 befintliga ruff-felen i repot är oförändrade. Flikraden, de fyra vyernas knappar och inställningsfliken är granskade visuellt via QWidget.grab().

Kvarstående risk: detektionsvyns rubrikrad är redan bred och inställningsknappen lägger till cirka 90 px, så raden går ihop på maximerat fönster men klipps på smala skärmar, precis som före ändringen.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-43
title: Inställningsknapp per flik i stället för inställningsflik
status: To Do
assignee: []
created_date: '2026-11-11T11:30:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/settings_view.py
  - xray_detector/ui/main_window.py
  - xray_detector/ui/training_view.py
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
- [ ] #1 Inställningsfliken är borta och flikraden har fyra flikar
- [ ] #2 Varje flik har en inställningsknapp som öppnar de inställningar som hör till fliken
- [ ] #3 Träningsschemat (nattfönster och inaktivitet) nås från träningsvyns inställningar
- [ ] #4 Temat går fortfarande att byta efter att inställningsfliken tagits bort
- [ ] #5 Befintliga sparade värden (ui/theme, training/night_start_hour, training/night_end_hour, training/inactivity_minutes) läses och skrivs som förut
- [ ] #6 Inställningsdialogen kan stängas utan att något ändras
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

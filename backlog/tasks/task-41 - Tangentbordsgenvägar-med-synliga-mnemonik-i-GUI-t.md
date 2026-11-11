---
id: TASK-41
title: Tangentbordsgenvägar med synliga mnemonik i GUI:t
status: To Do
assignee: []
created_date: '2026-11-11T11:23:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/main_window.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
priority: medium
type: enhancement
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GUI:t är i dag nästan helt musbaserat. Det enda som går att köra från tangentbordet är F11 för helskärm (MainWindow), Delete/Backspace för att ta bort markerad rektangel och Ctrl+hjul för zoom (annoteringscanvasen). Ingen etikett har mnemonik, så det syns inte heller vilka genvägar som finns.

Inventering av det som ska gå att köra från tangentbordet:
- Flikar: Detektion, Annotation, Dataset, Träning, Inställningar.
- Detektionsvyn: Fånga bilder, Detektion av/på, Försök igen (återanslutning i strömpanelen).
- Annoteringsvyn: Spara till dataset, Avbryt, Ta bort markerad, samt + och − för klasslistan.
- Datasetvyn: Ta bort markerade.
- Träningsvyn: Starta träning, Avbryt, Exportera COCO, Exportera YOLO.

Kravet på synlighet: Qt:s mnemonik med & i etiketten ger understruken bokstav och Alt+bokstav, men fungerar bara när bokstaven finns i ordet. Genvägar som inte är mnemonik, eller där bokstaven saknas i etiketten, ska visas inom parentes, till exempel "Avbryt (Esc)".

Att tänka på: annoteringscanvasen fångar redan Delete och Backspace, så nya genvägar får inte krocka med dem. Mnemonik måste vara unik inom varje vy, annars blir Alt+bokstav tvetydig. En genväg som hör till en knapp på en flik som inte är aktiv får inte utlösas.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Varje flik går att nå från tangentbordet och genvägen syns i flikraden
- [ ] #2 Fånga bilder och detektion av/på går att köra från tangentbordet
- [ ] #3 Spara till dataset, Avbryt och Ta bort markerad i annoteringsvyn går att köra från tangentbordet
- [ ] #4 Starta träning, Avbryt och export av COCO/YOLO går att köra från tangentbordet
- [ ] #5 Ta bort markerade i datasetvyn går att köra från tangentbordet
- [ ] #6 Knappar vars etikett innehåller genvägsbokstaven visar den understruken
- [ ] #7 Knappar vars etikett inte innehåller bokstaven visar genvägen inom parentes
- [ ] #8 Genvägarna krockar inte med canvasens Delete/Backspace eller Ctrl+hjul
- [ ] #9 En genväg som hör till en knapp på en inaktiv flik utlöses inte
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

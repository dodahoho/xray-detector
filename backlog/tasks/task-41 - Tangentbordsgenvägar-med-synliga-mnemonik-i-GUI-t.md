---
id: TASK-41
title: Tangentbordsgenvägar med synliga mnemonik i GUI:t
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-11T11:23:00Z'
updated_date: '2026-11-11T13:50:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/main_window.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
modified_files:
  - xray_detector/ui/shortcuts.py
  - xray_detector/ui/main_window.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
  - tests/test_shortcuts.py
  - tests/test_dataset_selection.py
  - tests/test_gui_smoke.py
  - README.md
  - groma/systems/xray-detector/containers/gui-app/components/shortcuts.md
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
- [x] #1 Varje flik går att nå från tangentbordet och genvägen syns i flikraden
- [x] #2 Fånga bilder och detektion av/på går att köra från tangentbordet
- [x] #3 Spara till dataset, Avbryt och Ta bort markerad i annoteringsvyn går att köra från tangentbordet
- [x] #4 Starta träning, Avbryt och export av COCO/YOLO går att köra från tangentbordet
- [x] #5 Ta bort markerade i datasetvyn går att köra från tangentbordet
- [x] #6 Knappar vars etikett innehåller genvägsbokstaven visar den understruken
- [x] #7 Knappar vars etikett inte innehåller bokstaven visar genvägen inom parentes
- [x] #8 Genvägarna krockar inte med canvasens Delete/Backspace eller Ctrl+hjul
- [x] #9 En genväg som hör till en knapp på en inaktiv flik utlöses inte
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Ny modul xray_detector/ui/shortcuts.py med mnemonic(), with_hint() och bind_shortcut().
2. Flikraden: &-mnemonik på alla fem flikar (D, A, S, T, I) så Alt+bokstav byter flik.
3. Detektionsvyn: Fånga bilder (F), Detektion av/på (O), Försök igen (G).
4. Annoteringsvyn: Spara till dataset (P), Ta bort markerad (B), Avbryt (Esc) samt Ctrl++/Ctrl+- för klasslistan.
5. Datasetvyn: Ta bort markerade (B), även när knappen visar antal.
6. Träningsvyn: Starta träning (R), Avbryt (Esc), Exportera COCO (E), Exportera YOLO (Y).
7. Mnemonikbokstäverna hålls unika mellan flikraden och synliga knappar; Esc/Ctrl++/Ctrl+- blir QShortcut med WindowShortcut-kontext på vyn, så en inaktiv flik inte utlöser dem.
8. Tester i tests/test_shortcuts.py: etiketter, unika bokstäver, Alt+bokstav per flik, inaktiv flik utlöser inte, Esc avbryter.
9. README: avsnitt om tangentbordsgenvägar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Ny modul ui/shortcuts.py: mnemonic() sätter & före bokstaven, with_hint() lägger genvägen inom parentes och bind_shortcut() binder Esc/Ctrl++/Ctrl+- som QShortcut med WindowShortcut-kontext på vyn.

Genvägar: flikraden &Detektion (D), &Annotation (A), Data&set (S), &Träning (T), &Inställningar (I); detektionsvyn &Fånga bilder (F), Detekti&on av/på (O), Försök i&gen (G) i ström 1 och Försök ige&n (N) i ström 2; annoteringsvyn S&para till dataset (P), Ta &bort markerad (B), Avbryt (Esc) samt Ctrl++/Ctrl+- för klasslistan; datasetvyn Ta &bort markerade (B); träningsvyn Sta&rta träning (R), Avbryt (Esc), &Exportera COCO (E), Exportera &YOLO (Y).

Mnemonikbokstäverna är unika per vy och krockar inte med flikraden, som alltid syns. Två genvägar med samma bokstav i samma fönster blir tvetydiga: första trycket flyttar bara fokus i stället för att aktivera. Därför får de två Försök igen-knapparna var sin bokstav.

Esc/Ctrl++/Ctrl+- binds på vyn. Qt aktiverar bara genvägar vars widget syns och är påslagen, så en inaktiv flik utlöser dem inte; samma regel ger AC 9 för mnemoniken, och en avstängd flik går inte att nå med sin mnemonik.

Avsteg: + och − har ingen bokstav i etiketten, så deras genväg står i tooltip i stället för inom parentes.

Verifiering: tests/test_shortcuts.py med 15 tester (etiketter, unika bokstäver, Alt+bokstav per flik, inaktiv flik utlöser inte, Esc avbryter, Ctrl++/Ctrl+-). Hela sviten: 223 passed, 1 skipped. Uppdaterade befintliga tester: test_dataset_selection.py (Ta &bort markerade) och test_gui_smoke.py (&Inställningar).
<!-- SECTION:NOTES:END -->

---
id: TASK-40
title: Tydlig spinner vid tidskrävande operationer
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-11T11:18:00Z'
updated_date: '2026-11-11T13:17:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/detection_view.py
  - xray_detector/application/model_registry.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/main_window.py
  - busy-indicator
  - background-task
modified_files:
  - xray_detector/ui/busy_indicator.py
  - xray_detector/application/background_task.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/main_window.py
  - tests/test_busy_indicator.py
  - tests/test_background_task.py
  - tests/test_busy_operations.py
  - tests/test_annotation_ux.py
  - tests/test_dataset_header.py
  - tests/test_dataset_selection.py
  - tests/test_gui_smoke.py
  - tests/test_pending.py
  - README.md
  - groma/config.json
  - groma/systems/xray-detector/containers/gui-app/components/busy-indicator.md
  - groma/systems/xray-detector/containers/gui-app/components/background-task.md
  - groma/systems/xray-detector/containers/gui-app/components/detection-view.md
  - groma/systems/xray-detector/containers/gui-app/components/dataset-view.md
  - groma/systems/xray-detector/containers/gui-app/components/training-view.md
  - groma/systems/xray-detector/containers/gui-app/components/annotation-view.md
priority: medium
type: enhancement
ordinal: 38000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Byte av detektionsmodell körs synkront i GUI-tråden. Uppmätt på RTX 5080 tar RF-DETR 2,1-7,2 s att ladda (nano 7,2 s, small 3,4 s, medium 3,6 s, large 2,1 s) och första YOLO-laddningen cirka 2,1 s eftersom CUDA-kontexten initieras; senare YOLO-byten tar 40-90 ms. Under laddningen fryser fönstret: statusradens "Laddar modell..." hinner aldrig ritas, så användaren kan inte se om appen hänger eller arbetar.

En spinner som bara läggs ovanpå den befintliga synkrona laddningen skulle också stå still, eftersom GUI-tråden är upptagen. Arbetet måste därför flyttas bort från GUI-tråden för att indikatorn ska animeras.

Samma behov finns för tre operationer som passerar en sekund i realistisk användning. Alla är uppmätta med 200 bilder i datasetet och körs synkront i GUI-tråden i dag:
- Datasetvyns omladdning: 580 ms, skalar linjärt mot antal bilder (cirka 3 s vid 1000). Körs vid flikbyte, efter sparning och efter borttagning.
- Export till COCO/YOLO: 92 respektive 143 ms, cirka 1 s vid 1500 bilder.
- Spara annoteringar (add_samples): 232 ms.

Dessutom tar enhetskontrollen vid start cirka 1,0 s eftersom torch initierar CUDA-kontexten. Den körs i MainWindow.__init__ innan fönstret visas, så den fördröjer starten i stället för att frysa en synlig vy. Den ska flyttas till en arbetstråd, inte få en spinner.

Källbytet behöver ingen indikator: arbetstråden öppnar kameran asynkront och set_source returnerar på 0-2 ms. Enhets- och modalitetslistningen ligger på 26-100 ms.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Detektionsvyn visar en tydlig, animerad upptagenindikator medan en modell laddas
- [ ] #2 Indikatorn syns innan arbetet börjar och försvinner när det lyckats eller misslyckats
- [ ] #3 Modelladdningen blockerar inte GUI-tråden, så indikatorn animeras och fönstret går att rita om under tiden
- [ ] #4 Modellväljaren är avstängd medan en laddning pågår, så två laddningar inte kan köra samtidigt
- [ ] #5 En misslyckad laddning ger samma felmeddelande som i dag och lämnar detektorn avstängd
- [ ] #6 Indikatorn är en egen komponent som kan användas på fler ställen än detektionsvyn
- [ ] #7 Indikatorn visas först efter en kort fördröjning, så snabba operationer inte ger en blinkning
- [ ] #8 Datasetvyn visar en animerad indikator medan bildlistan byggs om
- [ ] #9 Export till COCO och YOLO visar en animerad indikator medan den skriver
- [ ] #10 Spara annoteringar visar en animerad indikator medan datasetet skrivs
- [ ] #11 Enhetskontrollen vid start körs i en arbetstråd, så fönstret kan visas utan att vänta på CUDA-initieringen
<!-- AC:END -->

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
1. Ny komponent ui/busy_indicator.py: halvtransparent överlägg med snurra, text och fördröjning innan den visas.
2. Ny application/background_task.py: BackgroundTask som kör arbete i QThreadPool och levererar resultat/fel till GUI-tråden.
3. DetectionView: modelladdningen flyttas till arbetstråd, indikator + avstängd modellväljare under tiden, samma felmeddelande vid fel. Enhetskontrollen flyttas till arbetstråd utan indikator.
4. DatasetView: refresh() läser COCO och dekoder bilder till QImage i arbetstråd (mätt 826 av 870 ms för 200 bilder), widgetbygget kvar i GUI-tråden.
5. TrainingView: COCO-/YOLO-export i arbetstråd med indikator och avstängda exportknappar.
6. AnnotationView: add_samples + remove_pending i arbetstråd med indikator; MainWindow väntar in sparningen vid stängning.
7. Tester för komponenterna och de fyra vyerna; uppdatera befintliga tester som antog synkron omladdning.
8. README och groma-komponentkort uppdaterade.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat enligt planen.

Ny komponent ui/busy_indicator.py: halvtransparent överlägg med snurra och text, barn till den widget den täcker, 150 ms fördröjning innan den tänds och en timer som driver animationen. Ny application/background_task.py: BackgroundTask kör en funktion som QRunnable i Qt:s globala trådpool och rapporterar succeeded/failed/finished med köad anslutning till GUI-tråden; ett undantag blir ett felmeddelande i stället för en krasch i arbetstråden.

Detektionsvyn: modelladdningen sker i arbetstråden, modellväljaren stängs av under tiden och en pågående laddning kan inte startas om. Samma felmeddelande som förut ("Kunde inte ladda modell: ...") och detektorn lämnas avstängd. Enhetskontrollen flyttades till en arbetstråd utan indikator. pause_detection/resume_detection håller reda på pausläget så en laddning som blir klar under träning inte kopplar in detektorn igen.

Datasetvyn: refresh() läser COCO och dekoder bilderna till QImage i arbetstråden och bygger widgets i GUI-tråden. Mätt: 826 av 870 ms för 200 bilder var avkodning, widgetbygget cirka 45 ms. En omladdning som begärs medan en pågår körs när den första är klar, så sista läget vinner.

Träningsvyn: COCO-/YOLO-export i arbetstråd med indikator och avstängda exportknappar; ett fel blir ett statusmeddelande i stället för en krasch. Annoteringsvyn: add_samples + remove_pending i arbetstråd med indikator och avstängd spara-knapp. MainWindow väntar in sparning, omladdning och export vid stängning, och byter bara till detektionsfliken om annoteringsfliken är aktiv (sparningen är nu asynkron).

Verifiering, mätt på RTX 5080:
- RF-DETR nano: 6,31 s laddning, indikatorn visades efter 0,16 s, 12 unika snurrvinklar och 286 GUI-timertick under laddningen. Statusraden visade "Laddar modell..." och sedan "Modell laddad: RF-DETR nano".
- YOLO26 nano: 0,20 s, indikatorn hann tändas, 8 GUI-timertick.
- Datasetvyn med 200 bilder: 0,33 s omladdning, indikator efter 0,16 s, 11 GUI-timertick, 200 thumbnails.
- COCO-export 0,16 s och YOLO-export 0,17 s: ingen respektive en snurrvinkel, alltså ingen blinkning för den snabba operationen.
- Spara annoteringar 0,03 s: under fördröjningen, ingen indikator.

Tester: 24 nya tester i tests/test_busy_indicator.py, tests/test_background_task.py och tests/test_busy_operations.py. Befintliga tester som antog synkron omladdning och sparning väntar nu in arbetet (wait_for_refresh/wait_for_save). Sviten: 207 passed, 1 skipped. En test återstår att rätta: tests/test_gui_smoke.py::test_settings_and_theme_survive_restart faller på att fliktexten är '&Inställningar' i stället för 'Inställningar', vilket kommer från pågående TASK-41-arbete i samma arbetskopia och inte från den här uppgiften.

Ruff: inga nya anmärkningar (63 mot 64 före ändringen).
<!-- SECTION:NOTES:END -->

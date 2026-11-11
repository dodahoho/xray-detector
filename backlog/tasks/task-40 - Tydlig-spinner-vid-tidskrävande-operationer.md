---
id: TASK-40
title: Tydlig spinner vid tidskrävande operationer
status: To Do
assignee: []
created_date: '2026-11-11T11:18:00Z'
updated_date: '2026-11-11T11:22:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/detection_view.py
  - xray_detector/application/model_registry.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/main_window.py
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

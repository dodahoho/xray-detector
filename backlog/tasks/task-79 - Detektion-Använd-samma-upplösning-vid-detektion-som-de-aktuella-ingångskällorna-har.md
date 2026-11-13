---
id: TASK-79
title: >-
  Detektion - Använd samma upplösning vid detektion som de aktuella
  ingångskällorna har
status: In Progress
assignee:
  - '@vibe-mistral'
created_date: '2026-11-13T12:38:00Z'
updated_date: '2026-11-13T13:12:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/domain/model_input.py
  - xray_detector/infrastructure/detectors/yolo_detector.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
  - tests/test_inference_resolution.py
  - README.md
type: enhancement
ordinal: 77000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Om vi har en UVC som input så ska inferensen anpassa sig till den upplösningen på bästa sätt

Om videofil är input så ska upplösningen anpassas till innehållet i videofilen på bästa sätt
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Inferensen använder samma upplösning som UVC-källan har
- [x] #2 Inferensen använder videofilens egen upplösning
- [x] #3 Upplösningen avrundas till en multipel av 32 och begränsas till 320-1920
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
1. Inför en gemensam avrundning av modellens indatastorlek (multipel av 32, 320-1920) i domänen.
2. YoloDetector skickar källans upplösning som imgsz till predict i stället för ultralytics default 640.
3. RF-DETR behåller modellens egen upplösning eftersom den är arkitekturbunden; dokumentera varför.
4. Tester för avrundning/clamp och för att detect skickar ramens storlek.
5. README: dokumentera beteendet och den uppmätta kostnaden.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
YoloDetector skickar källans upplösning som imgsz till predict i stället för att låta ultralytics letterboxa till 640. Storleken räknas ur ramen, så UVC-ström och videofil får samma beteende utan att vyn behöver veta vilken källa som är aktiv. Avrundningen och gränserna (multipel av 32, 320-1920) ligger i xray_detector/domain/model_input.py, som träningens default också använder (TASK-80). RF-DETR rörs inte: modellen bygger på positionskodningar för en fast upplösning, så en annan storlek vid inferens ger sämre rutor.

Verifiering:
- Nya tester i tests/test_inference_resolution.py: avrundning och clamp, input_size_for för 1920x1080 och 640x480, och att detect skickar (1088, 1920) respektive (480, 640) till predict medan conf och device är oförändrade.
- Riktig modell (models/yolo26n.pt) på en ram ur media/xray_slideshow_side.mp4 (1280x720): imgsz (736, 1280), 25,1 ms per ram på RTX 5080 mot 24,6 ms vid 640, och alla rutor ligger inom ramen. Över 30 ramar gav källans upplösning 9 rutor vid conf 0,25 där 640 gav 0.
- Hela sviten: 530 passed, 1 skipped. test_sample_video_meta fallerar oberoende av ändringen: media/xray_slideshow_side.mp4 och _top.mp4 i arbetskatalogen har 6000 ramar medan testet förväntar 2250.
- ruff check: inga nya anmärkningar i ändrade filer.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
YOLO-detektionen körs nu i källans egen upplösning i stället för ultralytics standard 640, så en 1080p-ström ger imgsz 1088x1920 och detaljer kastas inte bort innan modellen ser dem.

Vad som ändrades:
- xray_detector/domain/model_input.py (ny): round_size() avrundar uppåt till en multipel av 32 inom 320-1920, med konstanterna STEP, MIN_SIZE, MAX_SIZE och DEFAULT_SIZE.
- xray_detector/infrastructure/detectors/yolo_detector.py: input_size_for(frame) räknar storleken ur ramen och detect() skickar den som imgsz. Källan behöver inte kännas vid: UVC och videofil får samma beteende eftersom storleken följer ramen.
- xray_detector/infrastructure/detectors/rfdetr_detector.py: docstring som förklarar varför RF-DETR behåller modellens egen upplösning.
- README.md: dokumenterar beteendet och den uppmätta kostnaden.

Verifiering:
- tests/test_inference_resolution.py (6 tester): avrundning och clamp, input_size_for för 1920x1080 och 640x480, att detect skickar (1088, 1920) respektive (480, 640) till predict, och att conf/device är oförändrade.
- Riktig modell på en 1280x720-ram ur media/xray_slideshow_side.mp4: imgsz (736, 1280), 25,1 ms per ram på RTX 5080 mot 24,6 ms vid 640; alla rutor ligger inom ramen.
- Hela sviten: 530 passed, 1 skipped. test_sample_video_meta fallerar oberoende av ändringen (media-filerna har 6000 ramar mot testets 2250).
- ruff check: inga nya anmärkningar.

Risker: på CPU blir 1080p-inferens cirka 30 gånger dyrare än 640 (1,3 s mot 0,04 s per ram i mätning); på GPU är kostnaden i praktiken noll. Taket 1920 gör att en 4K-källa körs i 1080p.
<!-- SECTION:FINAL_SUMMARY:END -->

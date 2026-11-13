---
id: TASK-80
title: >-
  Träning  - Default upplösning vid träning ska anpassa sig efter aktuellt
  dataset
status: In Progress
assignee:
  - '@vibe-mistral'
created_date: '2026-11-13T12:41:00Z'
updated_date: '2026-11-13T13:12:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/domain/model_input.py
  - xray_detector/domain/training.py
  - xray_detector/infrastructure/dataset_store/store.py
  - xray_detector/application/dataset_service.py
  - xray_detector/ui/training_view.py
  - tests/test_training_imgsz.py
  - README.md
type: feature
ordinal: 78000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
I vyn för träning finns ett värde att sätta bildstorlek i pixlar. Det är nu default satt till 640, men defaultvärdet borde sättas till den upplösning som applikationens dataset har.

Om det förekommer flera olika upplösningar kan det sättas till det vanligast förekommande.

Det bör också framgå bredvid inställningen vilka olika upplösningar som förekommer i applikationens dataset
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Default för bildstorlek är datasetets vanligast förekommande upplösning
- [x] #2 Alla upplösningar som förekommer i datasetet visas bredvid inställningen
- [x] #3 Ett eget val av bildstorlek behålls när datasetet ändras
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
1. DatasetStore.image_sizes() räknar bildupplösningarna ur dataset.json.
2. DatasetService.image_sizes() som fasad mot vyn.
3. imgsz_for(width, height) i domänen: längsta sidan avrundad uppåt till multipel av 32 inom spinnerns intervall.
4. TrainingView: default från vanligaste upplösningen tills användaren väljer en egen storlek, och en etikett bredvid inställningen som listar datasetets upplösningar.
5. Tester för vanligaste upplösning, etiketten och att användarens val stannar kvar.
6. README: dokumentera defaulten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Träningsvyns bildstorlek defaultar nu till datasetets vanligaste upplösning, och etiketten bredvid spinnern listar alla upplösningar med antal bilder. DatasetStore.image_sizes() räknar upplösningarna ur dataset.json (vanligaste först, största bilden vid lika antal) och DatasetService.image_sizes() är fasad mot vyn. imgsz_for() i domain/training.py tar den längsta sidan och avrundar uppåt till en multipel av 32, eftersom träningen letterboxar till en kvadrat. Defaulten följer datasetet tills användaren ändrar storleken själv; först då sparas training/imgsz, så ett eget val behålls och ett sparat värde från tidigare versioner vinner över datasetet.

Verifiering:
- Nya tester i tests/test_training_imgsz.py: imgsz_for (1920x1080 -> 1920, 1000x700 -> 1024, clamp), sortering i image_sizes, att bilder utan width/height hoppas över, default från vanligaste upplösningen, etikettens innehåll, att ett eget val överlever nya upplösningar, att sparat val återställs och att defaulten inte sparas.
- Renderad träningsvy med dataset 1920x1080 (2 bilder) + 640x480 (1): spinnern står på 1920 och etiketten visar 'Datasetets upplösningar: 1920x1080 (2), 640x480 (1)'.
- Hela sviten: 530 passed, 1 skipped. test_sample_video_meta fallerar oberoende av ändringen: media-filerna i arbetskatalogen har 6000 ramar medan testet förväntar 2250.
- ruff check: inga nya anmärkningar i ändrade filer.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Träningsvyns bildstorlek defaultar nu till datasetets vanligaste upplösning, och etiketten bredvid inställningen listar alla upplösningar som förekommer med antal bilder.

Vad som ändrades:
- xray_detector/infrastructure/dataset_store/store.py: image_sizes() räknar upplösningarna ur dataset.json, vanligaste först och största bilden vid lika antal; bilder utan width/height hoppas över.
- xray_detector/application/dataset_service.py: image_sizes() som fasad mot vyn.
- xray_detector/domain/training.py: imgsz_for() tar den längsta sidan och avrundar uppåt till en multipel av 32; TrainConfig.imgsz använder DEFAULT_SIZE.
- xray_detector/domain/model_input.py (ny): delade gränser och avrundning för både träning och inferens.
- xray_detector/ui/training_view.py: spinnern får datasetets default tills användaren väljer en egen storlek, etiketten 'Datasetets upplösningar: ...' bredvid, och training/imgsz sparas först vid ett eget val.
- README.md: dokumenterar defaulten och etiketten.

Verifiering:
- tests/test_training_imgsz.py (8 tester): imgsz_for, sortering, bilder utan dimensioner, default från vanligaste upplösningen, etiketten, eget val som överlever nya upplösningar, sparat val som återställs, och att defaulten inte sparas.
- Renderad träningsvy med 1920x1080 (2 bilder) + 640x480 (1): spinnern står på 1920 och etiketten visar 'Datasetets upplösningar: 1920x1080 (2), 640x480 (1)'.
- Hela sviten: 530 passed, 1 skipped. test_sample_video_meta fallerar oberoende av ändringen (media-filerna har 6000 ramar mot testets 2250).
- ruff check: inga nya anmärkningar.

Risker: ett sparat training/imgsz från en tidigare version vinner över datasetets default, eftersom det är användarens val. Det finns ingen väg tillbaka till 'följ datasetet' annat än att ändra storleken till samma värde som datasetet anger.
<!-- SECTION:FINAL_SUMMARY:END -->

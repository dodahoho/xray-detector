---
id: TASK-174
title: >-
  Detektion - annoteringsrutan för objekt släpar lite efter den det verkliga
  objekt som detekterats vid rörlig video
status: In Progress
assignee: []
created_date: '2026-11-20T22:06:00Z'
updated_date: '2026-11-20T22:41:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/infrastructure/detectors/smoothing.py
  - xray_detector/infrastructure/video/camera_service.py
  - tests/test_smoothing.py
  - tests/test_stream_worker.py
  - docs/beteende.md
type: enhancement
ordinal: 466000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När ett objekt detekteras i en frame verkar det vara en liten fördröjning innan det hinner ritas ut ovanpå videon vilket gör att i en video med objekt som förflyttar sig hinner objektet förflytta sig en bit från detektionsplatsen.

Finns det något sätt att lösa det eller är det bara att leva med?

Tänker att det bör gå att se hastigheten ett objekt förflyttar sig genom att jämföra detektioner mellan frames och även mäta den delay som finns för att kunna visa annoteringsrutan på rätt plats
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Annoteringsrutan visas där objektet är i ramen som visas, inte två ramar efter
- [x] #2 Utjämningen finns kvar: en stillastående ruta står still och ett hopp dämpas
- [x] #3 Dokumentationen beskriver prediktionen i stället för EMA-fördröjningen
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
1. Byt EMA:n i DetectionSmoother mot ett alpha-beta-filter som håller både position och hastighet per spårad ruta (alpha 0,5, beta = alpha²/(2-alpha)).

2. Låt update() ta emot dt och returnera rutan extrapolerad en ram, så rutan ritas där objektet är när ramen visas i stället för där det var två ramar tidigare.

3. Mät dt mellan varven i StreamWorker, nollställ vid detektorbyte och sätt ett tak så en paus i strömmen inte kastar iväg rutan.

4. Skriv om test_smoothing.py till hastighetstester och komplettera test_stream_worker.py med att rätt dt når utjämningen.

5. Uppdatera docs/beteende.md och docs/arkitektur.md: overlayn ligger inte längre en ram efter och utjämningen är ett alpha-beta-filter.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Orsak: två ramar staplades. StreamWorker skickar ram N med detektionerna från ram N-1 (TASK-37), och EMA:n med alpha 0,5 släpar (1-alpha)/alpha = 1 ram. Tillsammans visade rutan på ram N objektets position i ram N-2.

Mätt på media/xray_val_30x8_top.mp4 med models/best.pt, 60 ramar i 30 fps, objektets förflyttning 5,5 px per ram i median: före median 10,4 px, p90 12,1 px, max 13,3 px; efter median 1,0 px, p90 2,0 px, max 4,2 px. Hacket (std för andra differensen i visad mittpunkt) gick från 0,62 till 0,79 px, alltså fortfarande under pixeln.

Åtgärd: DetectionSmoother är ett alpha-beta-filter (alpha 0,5, beta = alpha²/(2-alpha) = 0,167) som håller position och hastighet per spårad ruta. update() tar emot dt och returnerar rutan extrapolerad en ram, så rutan ritas där objektet är när ramen visas. Andra träffen tar hela felet som hastighet, så en ny ruta inte börjar sitt liv med att släpa. StreamWorker mäter tiden mellan ramarna och skickar in den; dt nollställs vid detektorbyte och ett dt över 0,2 s extrapoleras inte, så en paus i strömmen inte kastar iväg rutan.

Verifiering: 12 tester i test_smoothing.py (nya: konstant hastighet hamnar rätt, stillastående står still, hopp dämpas, dt 0 och långt uppehåll extrapolerar inte) och ett nytt test i test_stream_worker.py som visar att ramtiden når utjämningen. Hela sviten 1041 passed, 1 skipped; ruff check går igenom.

Sidoeffekt: Fånga bilder använder samma rutor som ritas, så den sparade annoteringen blir en ram före bilden i stället för en ram efter. Samma felstorlek, motsatt riktning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Annoteringsrutan släpade två ramar efter objektet: StreamWorker skickar ram N med detektionerna från ram N-1 (TASK-37) och EMA:n med alpha 0,5 lägger till (1-alpha)/alpha = 1 ram. Utjämningen är nu ett alpha-beta-filter som håller position och hastighet per spårad ruta och extrapolerar rutan en ram, så den ritas där objektet är i ramen som visas.

Mätt på media/xray_val_30x8_top.mp4 med models/best.pt gick felet från median 10,4 px (p90 12,1, max 13,3) till median 1,0 px (p90 2,0, max 4,2), medan hacket låg kvar under pixeln (0,62 → 0,79 px). Hela sviten 1041 passed, 1 skipped, och ruff check går igenom.

Risk: Fånga bilder sparar samma rutor som ritas, så annoteringen blir en ram före bilden i stället för en ram efter. Ett dt över 0,2 s extrapoleras inte, så en paus i strömmen inte kastar iväg rutan.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-101
title: Loggen saknar spår av vad appen gjorde vid uppstart
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:32:00Z'
updated_date: '2026-11-16T20:50:00Z'
labels: []
dependencies: []
priority: medium
type: enhancement
ordinal: 201000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-90. Appens enda loggkanal är `ui/main_window.py:140`, som loggar varje statusradsmeddelande som `status: %s`. 101 av 183 rader i `logs/app.log` är sådana avskrifter, så loggen beskriver statusraden i stället för appen. Inget loggar vilken konfigfil som användes och vad den innehöll, vilken enhet som valdes, vilken viktfil som laddades och hur lång tid det tog, datasetets storlek vid start eller kamerauppräkningens resultat. Gapet mellan `Startar X-ray detector` (15:09:23,671) och `Modell laddad` (15:09:33,548) är tio sekunder som loggen inte förklarar alls. Dessutom saknar loggformatet process-id, trots att träningen körs i en separat OS-process (TASK-6), och app.log och training.log har inget gemensamt id så en träningskörning går inte att följa mellan filerna.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Uppstarten loggar vilken konfigfil som användes och vilka värden den satte
- [x] #2 Modelladdning loggar viktfil, familj, enhet och tidsåtgång
- [x] #3 Datasetets storlek och kamerauppräkningens resultat loggas vid start
- [x] #4 Loggformatet innehåller process-id
- [x] #5 En träningskörning har ett id som går att hitta i både app.log och training.log
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
1. LOG_FORMAT i application/app_config.py får %(process)d så app.log och training.log visar vilken process raden kom från.
2. app.py loggar vilken konfigfil som användes och vilka värden den satte (ny config_values()-hjälp i app_config.py).
3. ui/detection_view.py loggar modelladdning med viktfil, familj, enhet och tidsåtgång, samt vid start datasetets storlek och kamerauppräkningens resultat. RfDetrDetector får en device_label så enheten går att logga även för RF-DETR.
4. Träningen får ett körnings-id som skrivs både i app.log och i training.log.
5. Tester för konfigvärden, modelladdningens loggrad, uppstartsraderna, process-id i formatet och att körnings-id:t finns i båda filerna.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat: LOG_FORMAT har fått %(process)d efter tidsstämpeln. app.py loggar via _log_startup() vilken config.yaml som användes och config_values() med gällande värden. detection_view.py loggar kamerauppräkningen i __init__ och varje modelladdning med viktfil, familj, enhet och tidsåtgång (time.monotonic kring bakgrundsuppgiften). MainWindow._log_startup() loggar datasetets storlek via nya DatasetService.image_pair_count(). RfDetrDetector har fått en device_label, med cuda_device_label() delad med YoloDetector i base.py. TrainingView sätter run_id = körningskatalogens namn och skriver det i både training.log-rubriken och app.log vid start och avslut.

Verifierat: 7 nya tester i tests/test_startup_logging.py plus test_training_run_id_is_in_both_logs i tests/test_log_layout.py. Skarp appkörning gav raderna "Startar X-ray detector (konfig: default)", "Konfigvärden: ...", "Kameror: 0=USB Video, 1=Camera (NVIDIA Broadcast)", "Dataset: 9 bildpar, klasser=[...]" och "Modell laddad: RF-DETR large dvxray familj=rfdetr vikter=... enhet=CUDA (NVIDIA GeForce RTX 5080) på 6.8 s" med process-id [20980] på varje rad. Tio-sekundersgapet från TASK-90 är därmed förklarat: kamerauppräkning och modelladdning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Loggen beskriver nu appen i stället för statusraden. Loggformatet har process-id, så rader från appen och från träningsprocessen går att skilja åt. Uppstarten loggar vilken config.yaml som användes och vilka värden som gäller, datasetets storlek i bildpar, kamerauppräkningens resultat och varje modelladdning med viktfil, familj, enhet och tidsåtgång. RF-DETR fick en device_label så enheten går att logga även där, delad med YOLO via cuda_device_label(). En träningskörning får ett id från körningskatalogen som skrivs både i app.log och i training.log, så en körning går att följa mellan filerna. Verifierat med 8 nya tester och en skarp appkörning där tio-sekundersgapet från TASK-90 syns som kamerauppräkning plus 6,8 s modelladdning.
<!-- SECTION:FINAL_SUMMARY:END -->

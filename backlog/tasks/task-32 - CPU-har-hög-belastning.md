---
id: TASK-32
title: CPU har hög belastning
status: Done
assignee: []
created_date: '2026-11-10T12:12:00Z'
updated_date: '2026-11-10T12:42:00Z'
labels: []
dependencies: []
type: task
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Står att device är CUDA, dvs att GPU används, men under körninga av applikationen med två videofiler som källor är det CPU som är mest belastad. Undersök vad det beror på och om det är något som kan göras för att avlasta CPU
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Orsaken till CPU-lasten är utredd och dokumenterad
- [x] #2 CPU-lasten är avlastad utan att bildfrekvensen sjunker
- [x] #3 Åtgärden påverkar inte maskiner utan CUDA
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Utredning (demovideor 1280x720@30 fps, två strömmar, RTX 5080, 24 kärnor).

MÄTT LÄGE EFTER FIXEN: CPU ~100 % av en kärna (4 % av maskinen), GPU ~20 % utnyttjande, VRAM 223 MB, 59,6 fps (pacing-taket). Före fixen med RF-DETR small: 2176 % CPU.

VAR TIDEN GÅR (ultralytics egen mätning per ram): preprocess 0,32 ms, inference 4,81 ms (GPU), postprocess 0,73 ms, Python-overhead 0,13 ms = 5,99 ms. GPU:n gör alltså bara forward-passet och står stilla resten av tiden, därav 20 % utnyttjande.

ROTORSAK: PyTorch sprider de små CPU-tensorerna i för- och efterbearbetningen över torch.get_num_threads() = 12 trådar, och OpenCV över 24. Med två StreamWorker-trådar blir det 24 torch-trådar som slåss om samma små operationer. Mätt på RF-DETR small: 2176 % CPU med 12 trådar, 697 % med 4, 298 % med 2 och 102 % med 1 — vid oförändrade 59,6 fps. YOLO26m: 78 % -> 56 %. cv2.setNumThreads(1) gav ytterligare ~20 procentenheter för RF-DETR.

ÅTGÄRD: configure_inference_threads() i infrastructure/detectors/tuning.py sätter torch och OpenCV till en tråd, en gång, och bara när CUDA finns (på en CPU-only-maskin vinner flera trådar). Anropas från YoloDetector och RfDetrDetector.

TESTAT UTAN EFFEKT: cudaDeviceScheduleBlockingSync (ctypes mot cudart64_12.dll) i stället för spin-väntan gav ingen skillnad (82 % mot 79 % i medel över 3 par). Att ge varje worker en egen detektor i stället för en delad gav ingen skillnad i steady state (båda 59,6 fps).

VERIFIERING: 3 nya tester i tests/test_inference_tuning.py (begränsar med CUDA, lämnar orört utan, kör bara en gång). Hela sviten 139 passed, 1 skipped. End-to-end genom appens väg: RF-DETR small 97-106 % CPU vid 59,6 fps (från 2176 %), YOLO26m 76-101 % vid 59,6 fps.

NOTERAT: TASK-33 (ryckig detektion) vill jämna ut overlayn. Att sänka detektionsfrekvensen för att spara CPU skulle förvärra ryckigheten, så den åtgärden rekommenderas inte.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
CPU-lasten kom från PyTorch och OpenCV, inte från GPU:n. Med två strömmar i 30 fps spred torch de små CPU-tensorerna i modellernas för- och efterbearbetning över 12 trådar per worker, vilket för RF-DETR small kostade 2176 % CPU — medan GPU:n bara gjorde 4,8 ms forward-pass per ram och stod på 20 % utnyttjande. Med torch och OpenCV begränsade till en tråd (bara när CUDA finns) faller RF-DETR till ~100 % CPU och YOLO26m från 78 % till 56 %, med oförändrade 59,6 fps eftersom taket är videons 60 fps.

Verifierat: 3 nya tester, hela sviten 139 passed, 1 skipped, samt end-to-end-mätning genom appens väg före och efter.
<!-- SECTION:FINAL_SUMMARY:END -->

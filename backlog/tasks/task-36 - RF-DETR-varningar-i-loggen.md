---
id: TASK-36
title: RF-DETR varningar i loggen
status: Done
assignee: []
created_date: '2026-11-10T16:33:00Z'
updated_date: '2026-11-10T16:47:00Z'
labels: []
dependencies: []
type: bug
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Undersök orsak till dessa loggade WARNINGS och åtgärda eventuella brister i applikationen:

[2026-11-10 17:30:26] [WARNING] rf-detr - Using a different number of positional encodings than DINOv2, which means we're not loading DINOv2 backbone weights. This is not a problem if finetuning a pretrained RF-DETR model.
[2026-11-10 17:30:26] [WARNING] rf-detr - Using patch size 16 instead of 14, which means we're not loading DINOv2 backbone weights. This is not a problem if finetuning a pretrained RF-DETR model.
[2026-11-10 17:30:27] [INFO] rf-detr - File C:\Users\Ai1\.roboflow\models\rf-detr-medium.pth already exists with correct MD5 hash.
[2026-11-10 17:30:28] [WARNING] rf-detr - Model is not optimized for inference. Latency may be higher than expected. For full GPU throughput (e.g. ~8x on T4 via FP16 Tensor Cores), callmodel.inference(dtype=torch.float16).
[2026-11-10 17:30:28] [WARNING] rf-detr - Model is not optimized for inference. Latency may be higher than expected. For full GPU throughput (e.g. ~8x on T4 via FP16 Tensor Cores), callmodel.inference(dtype=torch.float16)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Orsaken till varje varningstyp är utredd och dokumenterad
- [x] #2 RF-DETR optimeras för inferens på GPU
- [x] #3 Tröskeländring laddar inte om modellen
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
Utredning av de tre varningstyperna:

1. 'Using a different number of positional encodings than DINOv2' och 'Using patch size 16 instead of 14' (dinov2.py:166 och :175): de utlöses när modellkonfigens positional_encoding_size * patch_size != 512 eller patch_size != 14. RF-DETR small/medium/large använder patch 16, så DINOv2-backbonens egna vikter laddas inte — men RF-DETR-checkpointen (rf-detr-<size>.pth) innehåller den finjusterade backbonen, så detektionen påverkas inte. Varningen är alltså väntad och ofarlig för inferens med förtränade vikter. Jag har inte tystat den: den är en riktig signal om man senare tränar en backbone från scratch.

2. 'Model is not optimized for inference' (detr.py:2717): appen anropade aldrig model.inference(). Nu anropas model.inference(dtype=torch.float16) när CUDA finns. Mätt på rfdetr-medium: 17,77 -> 9,22 ms per ram (-48 %), rutor inom 0,77 px (medel 0,35) och confidence inom 0,014 (medel 0,003) jämfört med ooptimerad modell över 80 ramar. 1 av 80 ramar fick olika antal detektioner, vilket är en träff precis på tröskeln. Optimeringen kostar cirka 1,4 s vid modelladdning och 69 MB extra VRAM.

3. Varningen förekom två gånger i loggen eftersom modellen skapades två gånger. Orsaken: conf_spin.valueChanged var kopplad till _on_model_changed, så varje ändring av confidence-tröskeln skapade en ny detektor och laddade modellen från disk igen (mätt: 1 modellskapande per tröskeländring). BaseDetector har nu set_confidence_threshold() och vyn anropar den i stället; mätt 0 modellskapanden per tröskeländring.

Verifiering: 5 nya tester i tests/test_detector_settings.py (tröskel uppdaterar detektorn utan omladdning, tröskel utan detektor, settern, RF-DETR optimerar med CUDA, hoppar över utan CUDA). Hela sviten 154 passed, 1 skipped, 3 av 3 gröna.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Loggvarningarna hade två åtgärdbara orsaker. RF-DETR optimerades aldrig för inferens; nu anropas model.inference(dtype=torch.float16) på GPU, vilket gav 17,8 -> 9,2 ms per ram med rutor inom 0,8 px. Och confidence-tröskeln var kopplad till modellbytet, så varje tröskeländring skapade en ny detektor och laddade modellen från disk igen — det gav också den dubbla varningen. Tröskeln uppdaterar nu detektorn direkt.

DINOv2-varningarna om positional encodings och patch size är väntade för RF-DETR-storlekarna och ofarliga: RF-DETR-checkpointen innehåller den finjusterade backbonen. De lämnas kvar som signal.

Verifierat: 5 nya tester, hela sviten 154 passed, 1 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->

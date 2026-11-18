---
id: TASK-107
title: Kan inte starta träning
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T07:49:00Z'
updated_date: '2026-11-17T08:43:00Z'
labels: []
dependencies: []
type: bug
ordinal: 193000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
YOLO träning fungerar, men inte RF-DETR

Loggutskrift i träningsvy när jag valde modell RF-DETR large dvxray och trycker Starta:

###

[2026-11-17_084829] Startar träning: C:\Users\Ai1\repo\xray-detector\models\checkpoint_best_total.pth på C:\Users\Ai1\.xray-detector\exports\rfdetr (100 epoker, imgsz 800, batch 16) -> C:\Users\Ai1\repo\xray-detector\models\trained\2026-11-17_084829
W1117 08:48:33.287000 17628 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "C:\Users\Ai1\repo\xray-detector\xray_detector\infrastructure\training\train_task.py", line 462, in <module>
    main()
  File "C:\Users\Ai1\repo\xray-detector\xray_detector\infrastructure\training\train_task.py", line 345, in main
    _train_rfdetr(args, device)
  File "C:\Users\Ai1\repo\xray-detector\xray_detector\infrastructure\training\train_task.py", line 432, in _train_rfdetr
    model = rfdetr_variant(args.weights)(resolution=args.imgsz)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ai1\repo\xray-detector\xray_detector\infrastructure\detectors\rfdetr_detector.py", line 41, in rfdetr_variant
    raise ValueError(f"Ok�nd RF-DETR-modell: {model_name}")
ValueError: Ok�nd RF-DETR-modell: C:\Users\Ai1\repo\xray-detector\models\checkpoint_best_total.pth
Tr�ning p� enhet: cuda
K�rningskatalog: C:\Users\Ai1\repo\xray-detector\models\trained\2026-11-17_084829
Träning avslutad (kod 1)
<!-- SECTION:DESCRIPTION:END -->

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
1. rfdetr_detector.py: _load_model(weights, resolution=None) laddar en .pth-snapshot med rfdetr.from_checkpoint utan att overrida dess upplosning, och bygger en storleksnyckel med upplosningen som forut.
2. train_task.py: _train_rfdetr anvander _load_model(args.weights, args.imgsz) och skickar resolution till train(), sa vyns bildstorlek galler aven for en snapshot (rfdetr raknar da om positionskodningarna).
3. Tester i tests/test_rfdetr.py: traning fran en .pth-snapshot, och att storleksnyckeln fortfarande byggs med upplosningen.
4. README: traning fran en egen RF-DETR-snapshot.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Orsak: _train_rfdetr slog upp basmodellen med rfdetr_variant(), som bara kanner till storleksnycklarna. En egen .pth-snapshot i models.json (t.ex. RF-DETR large dvxray -> checkpoint_best_total.pth) gav darfor ValueError: Okand RF-DETR-modell.

Fix: rfdetr_detector._load_model -> load_rfdetr_model(weights, resolution=None). En snapshot laddas med rfdetr.from_checkpoint, en storleksnyckel byggs med upplosningen som forut. _train_rfdetr skickar resolution till train() i stallet for att bara satta den vid konstruktionen: en snapshot bar sin egen upplosning i model_config, och train() raknar om positionskodningarna (verifierat: 704/pe 44 -> 800/pe 50).

Verifierat: 781 passed, 1 skipped. Ruff: inga nya fynd i andrade filer.

Tva blockerare till som bara gick att se nar krashen var borta, bada godkanda for uppgiften:

1. pytorch_lightning saknades helt i uv.lock. Projektets rfdetr-extra var rfdetr>=1.7 utan [train], sa train() gav ImportError innan forsta epoken. Extra:t ar nu rfdetr[train]>=1.7; uv lock/sync --extra cu128 --extra rfdetr installerade 30 paket och torch ar kvar pa 2.11.0+cu128 med CUDA.

2. COCO-exporten saknade area och iscrowd. rfdetr laser area rakt av i coco.py och dataloadern foll pa KeyError: 'area'. _coco_document skriver nu area = bbox w*h och iscrowd = 0, vilket ocksa ar vad COCO kraver.

Dessutom: MetricsTail laste metrics.csv fran en gammal byte-offset nar Lightning skrev om hela filen (_rewrite_with_new_header, som kors nar en ny kolumn tillkommer). Vyn visade Epok 6/1 och manifestet sparade epochs_completed 6 med tomma metrics for en enepokskorning. MetricsTail jamfor nu filens forsta rad mot den lasta headern och borjar om fran filens borjan nar den andrats; EpochAccumulator.reset() slanger ofullstandiga rader ur den gamla filen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RF-DETR-träning startar nu från en egen .pth-snapshot. Den rapporterade krashen kom av att _train_rfdetr slog upp basmodellen med rfdetr_variant(), som bara känner till storleksnycklarna; en snapshot i models.json gav ValueError: Okänd RF-DETR-modell. load_rfdetr_model() laddar nu en snapshot med rfdetr.from_checkpoint, och _train_rfdetr skickar resolution till train() så att vyns bildstorlek gäller även för en snapshot (rfdetr räknar då om positionskodningarna).

Två blockerare bakom den första krävde också ändringar: rfdetr-extra:t är nu rfdetr[train] (pytorch_lightning saknades helt i uv.lock), och COCO-exporten skriver area och iscrowd som rfdetr läser rakt av. Dessutom läser MetricsTail om metrics.csv när Lightnings header ändras, annars blev epokeventen fel (Epok 6/1 och epochs_completed 6 för en enepokskörning).

Verifierat med en riktig RF-DETR large-körning på GPU, 1 epok mot models/checkpoint_best_total.pth som basmodell: träningen gick igenom, checkpoint_best_total.pth skrevs, manifestet fick epochs_completed 1 med riktiga mätvärden (mAP50-95 0.0226) och EPOCH-eventet stämde med valideringstabellen. Hela sviten: 784 passed, 1 skipped. Ruff: inga nya fynd i ändrade filer.

Kvar att göra för användaren: inget, men en ny .pth-snapshot som basmodell tränas nu vidare från sina egna vikter med detektionshuvudet omställt till datasetets klassantal (rfdetr varnar om det i loggen).
<!-- SECTION:FINAL_SUMMARY:END -->

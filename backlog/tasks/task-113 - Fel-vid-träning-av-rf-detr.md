---
id: TASK-113
title: Fel vid träning av rf-detr
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T10:35:00Z'
updated_date: '2026-11-17T10:45:00Z'
labels: []
dependencies: []
type: bug
ordinal: 111000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Loggutskrift:

[2026-11-17_113227] Startar träning: C:\Users\Ai1\repo\xray-detector\models\checkpoint_best_total.pth på C:\Users\Ai1\.xray-detector\exports\rfdetr (100 epoker, imgsz 800, batch 8) -> C:\Users\Ai1\repo\xray-detector\models\trained\2026-11-17_113227
W1117 11:32:31.619000 12060 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
[2026-11-17 11:32:31] [WARNING] rf-detr - Using a different number of positional encodings than DINOv2, which means we're not loading DINOv2 backbone weights. This is not a problem if finetuning a pretrained RF-DETR model.
[2026-11-17 11:32:31] [WARNING] rf-detr - Using patch size 16 instead of 14, which means we're not loading DINOv2 backbone weights. This is not a problem if finetuning a pretrained RF-DETR model.
W1117 11:32:33.059000 12060 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
[2026-11-17 11:32:33] [WARNING] rf-detr - Using a different number of positional encodings than DINOv2, which means we're not loading DINOv2 backbone weights. This is not a problem if finetuning a pretrained RF-DETR model.
[2026-11-17 11:32:33] [WARNING] rf-detr - Using patch size 16 instead of 14, which means we're not loading DINOv2 backbone weights. This is not a problem if finetuning a pretrained RF-DETR model.
[2026-11-17 11:32:33] [WARNING] rf-detr - Checkpoint has 15 classes but model is configured for 1. The detection head will be re-initialized to 1 classes.
[2026-11-17 11:32:33] [WARNING] rf-detr - TensorBoard logging disabled: No module named 'tensorboard'. If using NumPy 2.x, ensure your TensorBoard installation is NumPy 2.0 compatible (the failure can originate from tensorboard.compat.tensorflow_stub). Install TensorBoard with: pip install tensorboard
Using bfloat16 Automatic Mixed Precision (AMP)
GPU available: True (cuda), used: True
TPU available: False, using: 0 TPU cores
\U0001f4a1 Tip: For seamless cloud logging and experiment tracking, try installing [litlogger](https://pypi.org/project/litlogger/) to enable LitLogger, which logs metrics and artifacts automatically to the Lightning Experiments platform.
Tr�ning p� enhet: cuda
K�rningskatalog: C:\Users\Ai1\repo\xray-detector\models\trained\2026-11-17_113227
[2026-11-17 11:32:33] [INFO] rf-detr - Building Roboflow train dataset with square resize at resolution 800
[2026-11-17 11:32:33] [INFO] rf-detr - Using multi-scale training with square resize and scales: [960]
loading annotations into memory...
Done (t=0.00s)
creating index...
index created!
[2026-11-17 11:32:33] [INFO] rf-detr - Building Roboflow val dataset with square resize at resolution 800
[2026-11-17 11:32:33] [INFO] rf-detr - Using multi-scale training with square resize and scales: [960]
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
Loading `train_dataloader` to estimate number of stepping batches.
loading annotations into memory...
Done (t=0.01s)
creating index...
index created!
+---------------------------------------------------------+
|   | Name        | Type         | Params | Mode  | FLOPs |
|---+-------------+--------------+--------+-------+-------|
| 0 | model       | LWDETR       | 33.8 M | train |     0 |
| 1 | criterion   | SetCriterion |      0 | train |     0 |
| 2 | postprocess | PostProcess  |      0 | train |     0 |
+---------------------------------------------------------+
Trainable params: 33.8 M
Non-trainable params: 0
Total params: 33.8 M
Total estimated model params size (MB): 135.318
Modules in train mode: 483
Modules in eval mode: 0
Total FLOPs: 0
Seed set to 42
W1117 11:32:38.116000 26200 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:38.090000 24116 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:38.161000 7924 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:38.231000 20560 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:38.419000 21744 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:38.361000 26544 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:38.427000 15548 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:38.532000 26100 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:39.311000 26200 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:39.398000 24116 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:39.460000 7924 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:39.538000 20560 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:39.626000 21744 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:39.690000 26544 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:39.766000 15548 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:39.880000 26100 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
[2026-11-17 11:32:44] [INFO] rf-detr - Skipping validation-loss computation: compute_val_loss='auto' found no scheduler or callback monitoring 'val/loss', so no 'val/loss' metric is logged this run. Set compute_val_loss=True to log it every validation epoch (for example to read the curve from metrics.csv, TensorBoard, or Weights & Biases).
W1117 11:32:48.221000 17716 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:48.220000 5740 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:48.442000 18548 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:48.325000 12660 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:48.373000 18780 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:48.407000 18340 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:48.586000 25124 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:48.512000 14268 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
W1117 11:32:49.525000 5740 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:49.525000 17716 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:49.614000 18548 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:49.619000 12660 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:49.663000 18780 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:49.702000 18340 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:49.765000 25124 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
W1117 11:32:49.810000 14268 .venv\Lib\site-packages\torch\utils\flop_counter.py:29] triton not found; flop counting will not work for triton kernels
           Val (ema) (Epoch 1/100) � Overall Metrics
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "C:\Users\Ai1\repo\xray-detector\xray_detector\infrastructure\training\train_task.py", line 482, in <module>
    main()
  File "C:\Users\Ai1\repo\xray-detector\xray_detector\infrastructure\training\train_task.py", line 359, in main
    _train_rfdetr(args, device)
  File "C:\Users\Ai1\repo\xray-detector\xray_detector\infrastructure\training\train_task.py", line 473, in _train_rfdetr
    self(**kwargs)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\detr.py", line 1437, in train
    trainer.fit(module, datamodule, ckpt_path=config.resume or None)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\trainer\trainer.py", line 584, in fit
    call._call_and_handle_interrupt(
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\trainer\call.py", line 49, in _call_and_handle_interrupt
    return trainer_fn(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\trainer\trainer.py", line 630, in _fit_impl
    self._run(model, ckpt_path=ckpt_path, weights_only=weights_only)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\trainer\trainer.py", line 1079, in _run
    results = self._run_stage()
              ^^^^^^^^^^^^^^^^^
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\trainer\trainer.py", line 1123, in _run_stage
    self.fit_loop.run()
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\loops\fit_loop.py", line 217, in run
    self.advance()
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\loops\fit_loop.py", line 469, in advance
    self.epoch_loop.run(self._data_fetcher)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\loops\training_epoch_loop.py", line 154, in run
    self.on_advance_end(data_fetcher)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\loops\training_epoch_loop.py", line 406, in on_advance_end
    self.val_loop.run()
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\loops\utilities.py", line 179, in _decorator
    return loop_run(self, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\loops\evaluation_loop.py", line 153, in run
    return self.on_run_end()
           ^^^^^^^^^^^^^^^^^
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\loops\evaluation_loop.py", line 296, in on_run_end
    self._on_evaluation_epoch_end()
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\loops\evaluation_loop.py", line 378, in _on_evaluation_epoch_end
    call._call_callback_hooks(trainer, hook_name)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\pytorch_lightning\trainer\call.py", line 228, in _call_callback_hooks
    fn(trainer, trainer.lightning_module, *args, **kwargs)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\training\callbacks\coco_eval.py", line 631, in on_validation_epoch_end
    self._compute_and_log(trainer, pl_module, "val")
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\training\callbacks\coco_eval.py", line 989, in _compute_and_log
    self._print_ema_only_summary(
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\training\callbacks\coco_eval.py", line 1396, in _print_ema_only_summary
    self._print_metrics_tables(trainer, "val (ema)", overall_ema, per_class_ema)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\training\callbacks\coco_eval.py", line 1519, in _print_metrics_tables
    _render_summary_tables(console, title_pfx, overall_rendered, per_class)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\utilities\console.py", line 278, in _render_summary_tables
    console.print(_build_summary_renderable(title_pfx, overall_rendered, per_class))
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rich\console.py", line 1704, in print
    with self:
         ^^^^
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rich\console.py", line 864, in __exit__
    self._exit_buffer()
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rich\console.py", line 820, in _exit_buffer
    self._check_buffer()
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rich\console.py", line 2055, in _check_buffer
    self._write_buffer()
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rich\console.py", line 2091, in _write_buffer
    legacy_windows_render(buffer, LegacyWindowsTerm(self.file))
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rich\_windows_renderer.py", line 19, in legacy_windows_render
    term.write_text(text)
  File "C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rich\_win32_console.py", line 402, in write_text
    self.write(text)
  File "C:\Users\Ai1\AppData\Roaming\uv\python\cpython-3.12.11-windows-x86_64-none\Lib\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input,self.errors,encoding_table)[0]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-63: character maps to <undefined>
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
1. train_task.py: _use_utf8_output() kopplar om sys.stdout och sys.stderr till UTF-8, anropad först i main(). rfdetr ritar tabeller med rich Console(force_terminal=True), som skriver box-tecken som cp1252 inte kan koda när stdout är en pipe.
2. Samma fix rättar mojibaken i träningsloggen: GUI:t läser processens stdout som UTF-8, men processen skrev cp1252, så 'Träning på enhet' blev 'Tr?ning p? enhet'.
3. Tester: enhetstest att _use_utf8_output() kopplar om en ström, och ett subprocesstest som kör med PYTHONIOENCODING=cp1252 och skriver box-tecken utan att krascha.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Orsak: rfdetr ritar valideringstabellen med rich Console(force_terminal=True) (rfdetr/utilities/console.py). Med stdout kopplad till en pipe använder Python cp1252 på Windows, och richs legacy_windows_render skriver box-tecken som cp1252 inte kan koda → UnicodeEncodeError i rich/_win32_console.py write_text.

Fix: train_task._use_utf8_output() kopplar om sys.stdout och sys.stderr till UTF-8 först i main(). Den tål strömmar utan reconfigure (t.ex. pytest-capsys) och sväljer OSError/ValueError.

Samma fix rättar mojibaken i träningsloggen: TrainingWorker läser processens stdout med decode('utf-8', errors='replace'), men processen skrev cp1252, så 'Träning på enhet: cuda' blev 'Tr?ning p? enhet: cuda' och 'Körningskatalog' blev 'K?rningskatalog'.

Verifierat med en riktig RF-DETR large-körning på GPU, 1 epok mot models/checkpoint_best_total.pth: valideringstabellen ritades utan krasch, TRAINING_DONE skrevs, exitkod 0, och 'Träning på enhet: cuda' / 'Körningskatalog:' syns korrekt i utmatningen. Två nya tester: ett subprocesstest med PYTHONIOENCODING=cp1252 som skriver box-tecken, och ett som kör helpern mot strömmar utan reconfigure. Hela sviten: 821 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RF-DETR-träningen kraschar inte längre på UnicodeEncodeError. rfdetr ritar valideringstabellen med rich Console(force_terminal=True), och med stdout kopplad till en pipe använder Python cp1252 på Windows, vilket inte kan koda richs box-tecken. Träningsprocessen kopplar nu om sys.stdout och sys.stderr till UTF-8 först i main(), så tabellerna går att rita oavsett vilken konsol processen fick.

Samma omkoppling rättar mojibaken i träningsloggen: GUI:t läser processens stdout som UTF-8, men processen skrev cp1252, så svenska tecken blev '?'. 'Träning på enhet: cuda' och 'Körningskatalog:' syns nu korrekt.

Verifierat med en riktig RF-DETR large-körning på GPU, 1 epok mot models/checkpoint_best_total.pth: valideringstabellen ritades, TRAINING_DONE skrevs och exitkoden var 0. Två nya tester: ett subprocesstest som kör med PYTHONIOENCODING=cp1252 och skriver box-tecken, och ett som kör helpern mot strömmar utan reconfigure. Hela sviten: 821 passed, 1 skipped. Ruff: inga nya fynd.
<!-- SECTION:FINAL_SUMMARY:END -->

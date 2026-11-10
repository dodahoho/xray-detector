---
id: TASK-36
title: RF-DETR varningar i loggen
status: To Do
assignee: []
created_date: '2026-11-10T16:33:00Z'
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

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

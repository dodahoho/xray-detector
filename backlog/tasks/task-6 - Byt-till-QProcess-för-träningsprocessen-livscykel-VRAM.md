---
id: TASK-6
title: Byt till QProcess för träningsprocessen (livscykel + VRAM)
status: To Do
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - arkitektur
  - träning
  - robusthet
dependencies: []
references:
  - trainer
  - training-process
  - main-window
priority: high
type: enhancement
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vibe-glm53 kör träningsprocessen via subprocess.Popen inuti en QThread. Funkar, men jämförelse_qwen38.md påpekar att processen orphanas om appen stängs, och jämförelse_argon.md avsnitt 2:3 beskriver bigpickles QProcess-mönster samt att antigravity/bigpickle frigör GPU-VRAM (torch.cuda.empty_cache()) när detektionen pausas för träning.

Byt TrainingWorker till QProcess: strömma stdout radvis till loggen, terminate() med kill()-fallback vid avbrott, stäng av processen i MainWindow.closeEvent (idag stoppas bara kameror), och töm CUDA-cachen när detektionen pausas vid träningsstart.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 träning körs i separat OS-process med strömmande logg (beteendet bibehålls)
- [ ] #2 avsluta appen under träning: processen avbryts utan orphan (eller fråga)
- [ ] #3 GPU-VRAM för detektorn frigörs när detektionen pausas för träning
<!-- AC:END -->

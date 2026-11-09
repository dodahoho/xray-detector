---
id: TASK-6
title: Byt till QProcess för träningsprocessen (livscykel + VRAM)
status: Done
assignee: []
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-09T12:31:00Z'
labels:
  - arkitektur
  - träning
  - robusthet
dependencies: []
references:
  - trainer
  - training-process
  - main-window
modified_files:
  - xray_detector/infrastructure/training/trainer.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/main_window.py
  - tests/test_training_worker.py
priority: high
type: enhancement
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vibe-glm53 kör träningsprocessen via subprocess.Popen inuti en QThread. Funkar, men jämförelse_qwen38.md påpekar att processen orphanas om appen stängs, och jämförelse_argon.md avsnitt 2:3 beskriver bigpickles QProcess-mönster samt att antigravity/bigpickle frigör GPU-VRAM (torch.cuda.empty_cache()) när detektionen pausas för träning.

Byt TrainingWorker till QProcess: strömma stdout radvis till loggen, terminate() med kill()-fallback vid avbrott, stäng av processen i MainWindow.closeEvent (idag stoppas bara kameror), och töm CUDA-cachen när detektionen pausas vid träningsstart.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 träning körs i separat OS-process med strömmande logg (beteendet bibehålls)
- [x] #2 avsluta appen under träning: processen avbryts utan orphan (eller fråga)
- [x] #3 GPU-VRAM för detektorn frigörs när detektionen pausas för träning
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
TrainingWorker ar nu QObject + QProcess (tidigare QThread + subprocess.Popen): samma signaler (progress, finished_training) och API (start/cancel), stdout strömmas radvis via readyReadStandardOutput med sammanslagna kanaler, och cancel() gor terminate() med kill()-fallback (3 s + 2 s) sa processen aldrig blir orphan. MainWindow.closeEvent fragar 'Avbryta träningen och avsluta?' nar en träning ker - Ja avbryter (terminate/kill) och stanger, Nej stoppar stangningen. pause_detection() slapper nu detektorinstansen och anropar torch.cuda.empty_cache() (garderad) sa träningsprocessen far hela GPU-minnet; resume_detection() aterbygger detektorn fran modellvalet. TrainingView aborterar via TrainingService och exponerar active_worker(). Verifierat: 4 nya tester (QProcess-streaming av tre rader + klar-kod 0, cancel av 30 s-process ger finished med ok=False och process avslutad, pause frigör VRAM via stubbad torch + resume aterbygger, closeEvent Yes->cancel / No->stangning stoppas); hel svit 63 passed.
<!-- SECTION:FINAL_SUMMARY:END -->

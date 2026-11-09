---
id: TASK-4
title: Bygg testsvit (enhet + GUI-smoke utan hårdvara)
status: Done
assignee:
  - '@glm53'
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-09T09:39:00Z'
labels:
  - test
  - kvalitet
dependencies: []
references:
  - dataset
  - annotation-view
  - video-capture
modified_files:
  - pyproject.toml
  - uv.lock
  - tests/conftest.py
  - tests/test_dataset_store.py
  - tests/test_export_split.py
  - tests/test_annotation_canvas.py
  - tests/test_stream_worker.py
  - tests/test_gui_smoke.py
  - xray_detector/ui/main_window.py
priority: high
type: task
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vibe-glm53 har helt saknar tester (tom tests/unit). Bäst testsvit finns i opencode-deepseek-flash (8 testfiler: coco, export, geometri, config, pending, träning, annotering-GUI) och opencode-bigpickle (enhet + pytest-qt UI-smoke med FakeDetector och syntetisk videosource, QT_QPA_PLATFORM=offscreen).

Se jämförelse_glm53.md punkt 2 och jämförelse_qwen38.md.

Prioritera: dataset-lagret (store/export/delete_images, capture-group), capture (source pacing, UVC-fallback-logik), annoteringscanvas (rita/flytta/resize/delete), GUI-smoke (stack MainWindow -> fånga -> annotera -> spara) med FakeDetector.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 pytest kan köras utan kameror/GPU (FakeDetector + syntetisk data)
- [x] #2 datasetlagret: add_samples/delete_images/export (inkl. split) har enhetstester
- [x] #3 ett GUI-smoketest täcker fånga -> annotera -> spara-flödet
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Lagg pytest i dev-beroenden + pytest-konfiguration i pyproject. 2. tests/conftest.py: session-qapp-fixture + FakeDetector + helpers. 3. tests/test_dataset_store.py: add/delete/group/metadata. 4. tests/test_export_split.py: train/val-split per grupp, labels, data.yaml, manifest. 5. tests/test_annotation_canvas.py: rita/flytta/resize/Delete-tangent. 6. tests/test_stream_worker.py: FileSource + FakeDetector i QThread utan kamera. 7. tests/test_gui_smoke.py: MainWindow: datasetvy -> dubbelklick -> annotering -> spara. 8. Kor hela sviten utan kameror/GPU.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
26 tester passerar pa 2.9 s utan kameror/GPU: datasetlagret (add/delete/group/metadata/versions), export (train-val-split per grupp, labels, data.yaml, manifest, determinism, COCO-export), annoteringscanvas (rita/flytta/resize/Delete/Backspace/result), StreamWorker med syntetisk videofil + FakeDetector i QThread, samt GUI-smoke (datasetvy -> dubbelklick -> annotering -> spara -> ny grupp, avbrott utan sparande, tema/inst-llningar over omstart). FakeDetector och syntetiska bilder i tests/conftest.py. Bieffekt: apply_theme flyttad till fore vy-konstruktion i MainWindow s- SettingsViewens temavaljare visar ratt val direkt.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Testsvit med 26 tester i fem moduler: datasetlagring, YOLO-export med grupp-medveten train/val-split, annoteringscanvas-event (rita/flytta/resize/Delete), StreamWorker mot syntetisk videofil med FakeDetector (QThread, ingen kamera), och GUI-smoke through hela fanga->annotera->spara-floedet via datasetvyn. pytest>=8 laggs i dev-gruppen och [tool.pytest.ini_options] pekar pa tests/. Korning: uv run pytest -> 26 passed pa ~3 s, ingen GPU eller kamera kravd. En produktionsjustering: temat appliceras nu fore vyerna byggs s hostsparat tema syns direkt i inst-allningsfliken.
<!-- SECTION:FINAL_SUMMARY:END -->

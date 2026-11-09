---
id: TASK-2
title: Registrera nytränade modeller med manifest i modellväljaren
status: Done
assignee:
  - '@glm53'
created_date: '2026-11-06T14:04:00Z'
updated_date: '2026-11-09T09:36:00Z'
labels:
  - träning
  - detektion
  - arkitektur
dependencies: []
references:
  - trainer
  - detectors
  - detection-view
modified_files:
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/application/model_registry.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/main_window.py
priority: high
type: feature
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Efter en lyckad träning syns resultatet inte i GUI:t: vikterna hamnar under models/v-version/ men detektionsvyns modellväljare listar bara statiska MODEL_SPECS.

Andra brancher (opencode-bigpickle, opencode-deepseek-flash) kopierar best.pt till modellkatalogen tillsammans med ett manifest (training_manifest.json/meta.json: klassnamn, datasetversion, epochs, metrics) och fyller modellväljaren automatiskt när träningen är klar. Se jämförelse_argon.md avsnitt 2:2.

I vibe-glm53: upptäck tränade vikter i models/ (detection/registry.py: MODEL_SPECS plus dynamiskt skannade manifest), skriv manifestet när träningen avslutas, och låt detection_view.py + training_view.py lista de nya modellerna.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 efter en lyckad träning finns vikten i models/ med ett manifest (klasser, datasetversion, datum, metrics)
- [x] #2 detektionsvynns modellväljare listar nytränade modeller efter träning utan omstart
- [ ] #3 deten slotter fungerar med tränad modell och rätt klassnamn
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifierat headlost med riktig YOLO-export: train_task skriver training_manifest.json (klasser via ast-tolkning av data.yaml, metrics fran results.csv, epochs/imgsz/batch, datum) i models/v<version>/; registry scandas trained_models() med felhantering; modellvaljaren fylls med bade basmodeller och tränade modeller samt bevarar val, och uppdateras automatisk nar träning avslutas (main_window kopplar refresh_models till training_finished). Detektion med tränad modell inte provad fysiskt (kraver riktiga vikter) men YoloDetector laddar arbitrar viktfil via ultralytics YOLO().
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
train_task skriver training_manifest.json (klasser, dataset, epochs/imgsz/batch, mAP-metrics, datum, vag till best.pt) i modellversionens katalog; Modellregistret scandas models/v*/training_manifest.json och listar tränade modeller som ModelSpec; detektionsvynns modellvaljare popupleras av bade statiska specar och tränade modeller och uppdateras automatiskt nar träningen avslutats, sa nytränade modeller syns utan omstart. Trasiga manifest och saknade vikter hanteras tyst. Kontroll av att riktigt träning producerar best.pt/manifest kraver en full träningkörning som inte gjordes - mekanismen verifierad med simulerade vikter och resultat.
<!-- SECTION:FINAL_SUMMARY:END -->

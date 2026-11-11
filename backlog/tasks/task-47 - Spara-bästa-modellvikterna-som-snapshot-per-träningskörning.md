---
id: TASK-47
title: Spara bästa modellvikterna som snapshot per träningskörning
status: To Do
assignee: []
created_date: '2026-11-11T11:51:00Z'
labels: []
dependencies: []
references:
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/application/model_registry.py
  - PLAN.md
priority: high
type: enhancement
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Kravet är att bästa modellvikterna alltid sparas som en snapshot. Nuvarande kod uppfyller det bara delvis.

Verifierat i befintlig kod:
- YOLO: best.pt skrivs i models/v<version>/<basmodell>/weights/best.pt och manifestet pekar på den. Men exist_ok=True och fast katalognamn gör att en ny körning med samma basmodell och version skriver över både best.pt och training_manifest.json. Det finns ingen historik och ingen tidsstämpel, trots att PLAN.md säger v{version}_{datum}.pt.
- RF-DETR: _write_manifest letar efter weights/best.pt, hittar ingen, och tar sedan senast ändrade *.pth. RF-DETR skriver checkpoint_best_total.pth i on_fit_end och därefter last_ema.pth, så mtime-valet pekar på last_ema.pth, det vill säga slutvikterna och inte bästa. checkpoint_best_total.pth är den dokumenterade bästa checkpoints.
- Avbruten eller kraschad träning: _write_manifest anropas bara efter att träningen kört klart, så bästa vikter från en avbruten körning registreras aldrig.
- Relativ --output: ultralytics lägger relativa project-sökvägar under runs/detect/, medan _train_yolo returnerar den relativa sökvägen. Manifestet skrivs då inte alls. Appen använder absolut sökväg, men CLI:t accepterar relativ.

Kravet är att varje körning får en unik snapshot av bästa vikterna, till exempel med tidsstämpel eller run-id, och ett manifest per körning med familj, basmodell, dataset, hyperparametrar, metrics och sökväg till snapshoten. Snapshoten ska vara den faktiskt bästa checkpoints för respektive familj och finnas kvar även om träningen avbryts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Varje träningskörning får en unik snapshot av bästa vikterna
- [ ] #2 En ny körning med samma basmodell och datasetversion skriver inte över föregående snapshot
- [ ] #3 YOLO-snapshoten är best.pt från körningen
- [ ] #4 RF-DETR-snapshoten är checkpoint_best_total.pth, inte last_ema.pth
- [ ] #5 Manifestet skrivs per körning och pekar på snapshoten
- [ ] #6 Manifestet innehåller familj, basmodell, dataset, hyperparametrar och metrics
- [ ] #7 En avbruten träning sparar bästa hittillsvarande vikter och manifest
- [ ] #8 Relativ --output ger samma snapshot-katalog som en absolut sökväg
- [ ] #9 Modellväljaren listar snapshots utan att äldre försvinner
- [ ] #10 Tester täcker snapshotnamn, manifestinnehåll och val av bästa checkpoint för båda familjerna
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

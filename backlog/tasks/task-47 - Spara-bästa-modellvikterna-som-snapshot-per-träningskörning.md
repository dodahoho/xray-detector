---
id: TASK-47
title: Träning - Spara bästa modellvikterna som snapshot per träningskörning
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-11T11:51:00Z'
updated_date: '2026-11-12T09:58:00Z'
labels: []
dependencies: []
references:
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/application/model_registry.py
  - PLAN.md
modified_files:
  - README.md
  - xray_detector/infrastructure/training/train_task.py
  - tests/test_training_snapshot.py
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Körningskatalogen blir unik: _prepare_run_dir lägger på _2, _3 när en tidigare körning redan har manifest, så en ny körning aldrig skriver över föregående snapshot.
2. --output tolkas absolut, så ultralytics inte lägger relativa project under runs/detect/.
3. _best_checkpoint väljer explicit bästa checkpoints per familj: yolo/weights/best.pt för YOLO och checkpoint_best_total.pth för RF-DETR, med checkpoint_best_ema/regular som reserv medan träningen pågår. last_ema.pth väljs aldrig.
4. Manifestet skrivs per körning med familj, basmodell, dataset, hyperparametrar, metrics, status, abort_reason och tidsåtgång, och skrivs om efter varje epok så en avbruten körning behåller bästa hittillsvarande vikter och manifest.
5. Tester för snapshotnamn, manifestinnehåll, val av bästa checkpoint för båda familjerna och att äldre körningar finns kvar i modellväljaren.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Körningskatalogen blir unik: _prepare_run_dir lägger på _2, _3 när katalogen redan har ett manifest. --output tolkas absolut via _output_path, så ultralytics inte lägger relativa project under runs/detect/. _best_checkpoint väljer explicit bästa checkpoints: yolo/weights/best.pt för YOLO och checkpoint_best_total.pth för RF-DETR, med checkpoint_best_ema/regular som reserv medan träningen pågår; last_ema.pth väljs aldrig. Manifestet skrivs om efter varje epok med familj, basmodell, dataset, hyperparametrar, metrics, epoker, status, abort_reason och tider. Verifierat med två riktiga körningar mot samma --output: den andra hamnade i run8_2 med eget manifest och egen best.pt, och modellväljaren listade båda körningarna.
<!-- SECTION:NOTES:END -->

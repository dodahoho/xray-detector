---
id: TASK-89
title: >-
  Jämför kod för modellträning och visualisering för att hitta eventuella
  brister
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T14:49:00Z'
updated_date: '2026-11-16T16:30:00Z'
labels: []
dependencies: []
type: task
ordinal: 87000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Det finns ett lokalt projekt xray_modeltrainer där träning har genomförts av både yolo26large och rf-detr large. Träningen visualiserades där i en html dashboard. Jämför xray_detector med xray_modeltrainer med avseende på modellträning för att se om det är något som kan förbättras i detta projekt
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Läs träningskedjan i xray_detector: infrastructure/training/{train_task,trainer,epoch_metrics,overfitting}.py, application/{training_service,training_history}.py, domain/training.py, ui/{training_view,training_chart}.py samt dataset_store/export.py.
2. Läs motsvarande delar i xray_modeltrainer: train_yolo.py, train_rfdetr.py, monitor.py, heartbeat.py, sources.py, dashboard.py, evaluate.py, split.py, diagnose.py.
3. Jämför per område: hyperparametrar, augmentation, RF-DETR-argument, reproducerbarhet, split-strategi, utvärdering, progressrapportering, diagnos.
4. Skriv jämförelsen som anteckning i uppgiften med konkreta fil- och radreferenser.
5. Skapa uppföljningsuppgifter för de brister som är värda att åtgärda, med prioritet.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Jämförelse genomförd 2026-11-16. Källorna är `xray_detector/infrastructure/training/`, `application/training_*.py`, `ui/training_*.py`, `infrastructure/dataset_store/export.py` mot `xray-modeltrainer/src/xray_trainer/`.

### Sammanfattning

xray_detector har en bättre *drift* kring träningen (QProcess, manifest per körning, avbrott, schemaläggning, GUI-graf). xray_modeltrainer har en bättre *träningsmetodik* (hyperparametrar, augmentation, utvärdering, split, diagnos). Det som saknas i xray_detector är framför allt metodik, inte infrastruktur.

### 1. Hyperparametrar för YOLO saknas helt

`train_task.py:_train_yolo` skickar bara `data, epochs, imgsz, batch, device, project, name, exist_ok, patience`. Allt annat blir ultralytics defaults (verifierat mot installerad version):

| Parameter | xray_detector (default) | xray_modeltrainer |
|---|---|---|
| optimizer | `auto` | `AdamW` |
| lr0 | `0.01` | `0.001` |
| cos_lr | `False` | `True` |
| seed | `0` | `42` |
| mosaic | `1.0` | `0.3` |
| close_mosaic | `10` | `15` |
| degrees | `0.0` | `30` |
| hsv_s | `0.7` | `0.2` |
| patience | 10 (vaktens värde) | 30 |

`degrees=0.0` och `mosaic=1.0` är särskilt olämpliga för röntgen med godtycklig objektrotation. `optimizer=auto` väljer SGD eller AdamW utifrån epokantal, så samma konfiguration kan ge olika optimerare vid olika epokantal.

### 2. RF-DETR får inte de argument den behöver

`train_task.py:_train_rfdetr` skickar `dataset_dir, epochs, batch_size, device` plus early stopping. Verifierat mot `rfdetr.config.TrainConfig`:

- `num_workers` default är **2**. modeltrainer sätter 8 med motiveringen att 2 svälter GPU:n på stora dataset.
- `seed` default är **None**.
- `resolution` finns inte i `TrainConfig` utan i `ModelConfig`, alltså som konstruktorargument. xray_detector skickar aldrig `imgsz` till RF-DETR: **GUI:ts bildstorlek ignoreras tyst för RF-DETR**. Det är en bugg, inte bara en saknad inställning.
- `batch` default är 16 för båda familjerna. modeltrainer använder 4 för RF-DETR large eftersom auto-batch-proben får OOM på 16 GB vid resolution 704 och inte kan återhämta sig.

`best_model_metric` (default `map`) och `early_stopping_min_delta` (default `0.001`) är redan rätt och behöver inte sättas.

### 3. Ingen utvärdering utanför träningen

modeltrainer har `evaluate.py`: mAP50-95 totalt och **per vy (OL/SD)**, samt falsklarm per bild på en held-out stress-mängd vid den konfidenströskel som ger 95 % recall. xray_detector har ingen utvärderingsfunktion alls. Enda kvalitetstalet är val-mAP från träningen, som inte säger något om falsklarm på negativa bilder — vilket är det som avgör om modellen är driftsättbar i en röntgenapp.

### 4. Test-delen är en kopia av val

`export.py:export_rfdetr` rad 173: `for split, images in (("train", train), ("valid", val), ("test", val))`. Test är identisk med val, så ett "test"-mått är i praktiken ett val-mått. modeltrainer håller train/val/test åtskilda och har dessutom en separat stress-mängd.

### 5. Delningen är inte stratifierad

`export.py:train_val_split` blandar fångstgrupper slumpmässigt (seedat). Grupperingen förhindrar läckage mellan train och val, vilket är bra, men det finns ingen stratifiering: en ovanlig klass kan saknas helt i val, och då blir val-mAP både brusigt och missvisande. modeltrainer stratifierar på klassuppsättningssignatur och lägger små grupper först så att ovanliga klasser inte svälts av avrundning.

### 6. Ingen förloppsrapportering inom epoken

modeltrainer skriver `progress.json` (atomiskt, throttlat till 2 s) med epok, steg och totalt antal steg, så dashboarden visar hur långt epoken kommit. xray_detector rapporterar bara per epok. En epok på ett stort dataset kan ta flera minuter, och under den tiden står GUI:t still utan att användaren kan se om träningen lever.

### 7. Ingen diagnos av en avslutad körning

modeltrainer har `OverfitMonitor.verdict()` som klassar körningen som `still improving` / `overfitting` / `plateaued` med konkret råd, och `diagnose.py` skriver ut domen ur en sparad trace. xray_detectors `OverfittingGuard` avbryter bara — den säger aldrig efteråt vad körningen led av, och det finns ingen motsvarighet till `diagnose.py` för en redan avslutad körning.

### 8. Avbrottet ser ut som ett fel

`OverfittingGuard` stoppar via `trainer.stop = True`, vilket gör att körningen avslutas och manifestet får `status: "aborted"` med överträning som orsak. En konvergerad körning som vakten stoppar är ett lyckat utfall, men historiken visar den som avbruten. modeltrainer använder ultralytics `patience` (riktig early stopping) och får `completed`.

### 9. Det som är bättre i xray_detector och inte ska ändras

- Träningen går i egen OS-process via QProcess med terminate/kill-fallback (TASK-6).
- Manifest per körning som skrivs om varje epok, så en hårdstoppad körning ändå pekar på bästa vikterna (TASK-47).
- Explicit val av bästa checkpoint per familj i stället för senast ändrad fil.
- Strukturerade `EPOCH {json}`- och `ABORT {json}`-rader i stället för att parsa fri text.
- Historikvy med export av vikter och manifest (TASK-59).
- Schemaläggning till nattfönster eller inaktivitet (TASK-7).

### Åtgärdsförslag, i prioritetsordning

1. Skicka `imgsz` som `resolution` till RF-DETR (bugg, tyst ignorerad inställning).
2. Sätt `num_workers` för RF-DETR.
3. Sätt explicita YOLO-hyperparametrar: optimizer, lr0, cos_lr, seed.
4. Sätt augmentation lämplig för röntgen: degrees, mosaic, close_mosaic, hsv_s.
5. Separat test-del i stället för kopia av val.
6. Stratifierad delning på klassuppsättning.
7. Utvärderingsfunktion med mAP per vy och falsklarm per bild.
8. Förloppsrapportering inom epoken.
9. Dom över avslutad körning i historikvyn.
10. Sätt `batch` default per familj.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Jämförelsen är genomförd och dokumenterad i uppgiftens anteckningar. xray_detector har bättre drift kring träningen (QProcess, manifest per körning, avbrott, schemaläggning, GUI-graf); xray_modeltrainer har bättre träningsmetodik. Nio konkreta brister hittades, varav en är en bugg: GUI:ts bildstorlek når aldrig RF-DETR eftersom `resolution` ligger i `ModelConfig` och inte i `TrainConfig`, så inställningen ignoreras tyst. Övriga: YOLO-träningen ärver ultralytics defaults för optimizer och augmentation (degrees 0.0, mosaic 1.0, hsv_s 0.7 — olämpligt för röntgen), RF-DETR får inte num_workers eller seed, RF-DETR-exportens test-del är en kopia av val, delningen är inte stratifierad, det finns ingen utvärdering utanför träningen, ingen förloppsrapportering inom epoken och ingen dom över hur en körning slutade. Uppföljningsuppgifter skapade: TASK-91 till TASK-97. Verifiering: hela testsviten körd, 667 passed och 1 skipped, oförändrat eftersom ingen kod ändrades. DoD #5 (Code committed) är inte ikryssad: uppgiften producerade ingen kodändring, så det finns inget att committa.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-118
title: Träning med ramverkens egna "early stopping"
status: Done
assignee:
  - '@david'
created_date: '2026-11-17T13:50:00Z'
updated_date: '2026-11-17T14:14:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/infrastructure/training/train_task.py
  - xray_detector/infrastructure/training/overfitting.py
  - tests/test_training_params.py
  - tests/test_overfitting.py
  - tests/test_training_verdict.py
  - xray_detector/ui/training_view.py
  - README.md
  - >-
    groma/systems/xray-detector/containers/training-process/components/overfitting.md
type: enhancement
ordinal: 182000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Träningen kan nu avbrytas när den visar tendens på överträning. Jag vill att denna funktion ska använda de inbyggda funktionerna för sk early stopping i ramverken från ultralytics och rfdetr. För YOLO används parametern patience för att ange hur många epoker man tillåter att köra vidare trots att valideringsresultatet inte blir bättre. Använd dessa inbyggda funktioner (om det inte redan görs så). Förenkla sedan befintlig kod om det går

Ex 1 (yolo):
from ultralytics import YOLO
model = YOLO("yolo26l.pt")
results = model.train(
    data="path/to/dataset",
    epochs=200,
    patience=15
)

Ex2 (rfdetr):
from rfdetr import RFDETRLarge
from rfdetr.config import TrainConfig
model = RFDETRLarge()
train_config = TrainConfig(
    dataset_dir="path/to/dataset",
    epochs=200,
    early_stopping=True,
)
model.train(train_config=train_config)
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
1. Låt ramverkens egna early stopping vara enda mekanismen: ultralytics `patience` för YOLO och `early_stopping`/`early_stopping_patience` för RF-DETR.
2. Ta bort den egna vakten: `overfitting.py`, `_StopSignal`, `_apply_stop` och `on_fit_epoch_end`-callbacken.
3. Avgör efter träningen om körningen stoppade tidigt (färre genomförda epoker än begärda) och rapportera orsaken som ABORT-rad till GUI:t och som `stop_reason` i manifestet.
4. Uppdatera testerna och README.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Ramverkens egna early stopping är nu enda mekanismen: YOLO får `patience` (0 när valet är av) och RF-DETR `early_stopping`/`early_stopping_patience`. Den egna vakten (`overfitting.py` med `OverfittingGuard`), `_StopSignal`, `_apply_stop` och `on_fit_epoch_end`-callbacken är borttagna. Ett tidigt stopp avgörs i stället efter träningen: `_finish_state` jämför rapportörens `epochs_completed` med `--epochs` och sätter `status=aborted`, `stop_reason=overfitting` samt en `ABORT`-rad med orsaken, som GUI:t visar och manifestet sparar som `abort_reason`. Testerna är omskrivna: vakttesterna är borta, `_finish_state`-testerna ligger kvar i test_training_verdict.py med nya signaturen, och test_overfitting.py täcker patience/early_stopping, rapportören samt två körningar av `main()` som visar ABORT-raden respektive en fullständig körning. README och verktygstipset i träningsvyn beskriver den nya mekanismen. Groma-komponenten `overfitting` är borttagen eftersom filen den ägde är borta.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Träningen använder nu ultralytics `patience` och rfdetr `early_stopping` som enda mekanism för tidigt stopp; den egna överträningsvakten och dess callback är borttagna (train_task.py 115 rader ändrade, overfitting.py 68 rader borttagna). Ett tidigt stopp upptäcks efter träningen genom att jämföra genomförda epoker med begärda och rapporteras som ABORT-rad till träningsvyn och som `stop_reason`/`abort_reason` i manifestet, så historikvyn fortsätter visa `Avbruten (överträning)`. Verifierat med hela testsviten: 845 passed, 1 skipped. Risk: stoppet upptäcks på epokantal, så en körning som avslutas i förtid av ett annat skäl (t.ex. ultralytics tidsgräns) klassas också som överträning.
<!-- SECTION:FINAL_SUMMARY:END -->

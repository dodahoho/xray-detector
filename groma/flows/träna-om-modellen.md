---
type: Groma Flow
title: Träna om modellen
groma:
  id: träna-om-modellen
---

Operatören exporterar den valda datasetversionen och startar träningen från GUI:t. TrainingWorker startar träningsprocessen och bevakar dess utmatning rad för rad. Modellvikterna sparas i models-katalogen under respektive datasetversion.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Säkerhetsoperatör](../actors/säkerhetsoperatör.md) | [Träningsvy](../systems/xray-detector/containers/gui-app/components/training-view.md) | Startar träning |
| [Träningsvy](../systems/xray-detector/containers/gui-app/components/training-view.md) | [Datasetlagring](../systems/xray-detector/containers/gui-app/components/dataset.md) | Exporterar YOLO-dataset |
| [Träningsvy](../systems/xray-detector/containers/gui-app/components/training-view.md) | [Träningskörning](../systems/xray-detector/containers/gui-app/components/trainer.md) | Startar TrainingWorker |

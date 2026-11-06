---
type: Groma Flow
title: Fånga och annotera bilder
groma:
  id: fånga-och-annotera-bilder
---

Operatören fångar bildpar från de två strömmarna, annoterar dem i annoteringsvyn och sparar dem som en fångstgrupp i datasetet.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Säkerhetsoperatör](../actors/säkerhetsoperatör.md) | [Detektionsvy](../systems/xray-detector/containers/gui-app/components/detection-view.md) | Fångar bildpar |
| [Huvudfönster](../systems/xray-detector/containers/gui-app/components/main-window.md) | [Annoteringsvy](../systems/xray-detector/containers/gui-app/components/annotation-view.md) | Laddar fångsten i annoteringsvyn |
| [Annoteringsvy](../systems/xray-detector/containers/gui-app/components/annotation-view.md) | [Datasetlagring](../systems/xray-detector/containers/gui-app/components/dataset.md) | Sparar annoteringar som fångstgrupp |

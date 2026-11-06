---
type: Groma Flow
title: Detektera objekt live
groma:
  id: detektera-objekt-live
---

Kameraramar detekteras i realtid i varje strömtråd och ritas som overlay i detektionsvyn.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Säkerhetsoperatör](../actors/säkerhetsoperatör.md) | [Detektionsvy](../systems/xray-detector/containers/gui-app/components/detection-view.md) | Väljer källor och modell |
| [Detektionsvy](../systems/xray-detector/containers/gui-app/components/detection-view.md) | [Videoinspelning](../systems/xray-detector/containers/gui-app/components/video-capture.md) | Startar kameratrådar |
| [Videoinspelning](../systems/xray-detector/containers/gui-app/components/video-capture.md) | [Detektorer](../systems/xray-detector/containers/gui-app/components/detectors.md) | Detekterar varje ram |

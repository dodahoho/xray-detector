---
type: C4 Component
title: Resursmätning
status: stable
groma:
  id: resources
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/infrastructure/system/resources.py
description: Samplar appens CPU-, RAM-, GPU- och VRAM-användning.
---

ResourceMonitor läser den egna processens CPU och RAM via psutil och GPU/VRAM via torch.cuda. ResourceUsage är ett ögonblicksvärde där ett fält är tomt när resursen inte kan mätas, till exempel GPU utan CUDA. Detektionsvyn visar värdena som staplar i den övre raden och uppdaterar dem varje sekund.

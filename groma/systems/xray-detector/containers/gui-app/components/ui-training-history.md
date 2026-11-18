---
type: C4 Component
title: Training history
status: stable
groma:
  id: ui-training-history
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/training_history.py
description: Listar tidigare träningar med export och utvärdering.
---

Tabell med en rad per körning ur models/trained/: körning, basmodell, epoker, tidsåtgång, mAP50-95 och status, nyast först. Raden under listan visar vald körnings parametrar och domen. Knapparna Exportera modell, Ta bort träning och Utvärdera arbetar på det valda objektet; utvärderingen körs i en bakgrundsuppgift.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/training_history.py](../../../../../../xray_detector/ui/training_history.py) | [xray_detector/application/evaluation.py](../../../../../../xray_detector/application/evaluation.py) | Startar utvärderingen av vald körning | direkt anrop |

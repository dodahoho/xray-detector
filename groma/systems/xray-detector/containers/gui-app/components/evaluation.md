---
type: C4 Component
title: Evaluation
status: stable
groma:
  id: evaluation
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/application/evaluation.py
description: Utvärderar en tränad modell och sparar rapporten i körningens katalog.
---

Kör en vald tränad modell över en vald delmängd (Test, Val eller Alla) utan att starta en träning och sparar evaluation.json i körningens katalog, så två körningar kan jämföras i efterhand. Rapporten visar mAP50-95 och mAP50 totalt och per vy samt falsklarm per bild på de negativa bilderna vid den konfidenströskel som ger 95 % recall på de positiva.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/application/evaluation.py](../../../../../../xray_detector/application/evaluation.py) | [xray_detector/infrastructure/training/metrics.py](../../../../../../xray_detector/infrastructure/training/metrics.py) | Räknar mAP och falsklarm | numpy |

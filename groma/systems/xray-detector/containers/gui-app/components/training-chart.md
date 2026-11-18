---
type: C4 Component
title: Training chart
status: stable
groma:
  id: training-chart
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/training_chart.py
description: Graf över loss och mAP per epok.
---

Två QtCharts-grafer i träningsvyn, en för loss och en för mAP, med egen axel per serie eftersom skalorna skiljer sig. QtCharts följer med PySide6 och kräver ingen ny dependency. Grafen töms när en ny körning startar och visar bara de epoker som rapportören skickat.

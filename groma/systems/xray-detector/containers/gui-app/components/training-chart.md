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
description: Graf över loss och mAP per epok, ritas med QPainter i widgetens palett.
---

Två grafer i träningsvyn, en för loss och en för mAP, med egen axel per serie eftersom skalorna skiljer sig. Grafen ritas med QPainter: axlar, rutnät, polylinjer, markörer och legend hämtar bakgrund och text ur widgetens palett, så den följer appens ljusa och mörka tema. QtCharts används inte, eftersom modulen är utfasat i Qt 6.8 och borttaget i Qt 6.10. Grafen töms när en ny körning startar och visar bara de epoker som rapportören skickat.

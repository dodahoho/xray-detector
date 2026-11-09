---
type: C4 Component
title: Klassfärger
status: stable
groma:
  id: colors
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/colors.py
      symbol: class_color
  group: Användargränssnitt
description: Deterministisk klass-till-färg-mappning delad av detektion och annotering.
---

class_color() mapper kanda klasser till fast index i klasslistan och okanda till CRC32, sa samma klass far samma farg vid varje appstart (Pythons hash() seedas slumpvis per process och ersattes ur TASK-5). Anvands av StreamPanels overlay och annoteringsrektanglar; CLASS_COLORS ar paletten.

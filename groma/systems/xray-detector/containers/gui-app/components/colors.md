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

class_color() mappar kända klasser till fast index i klasslistan och okända till CRC32, så samma klass får samma färg vid varje appstart (Pythons hash() seedas slumpvis per process och ersattes ur TASK-5). Används av StreamPanels overlay och annoteringsrektanglar; CLASS_COLORS är paletten.

---
type: C4 Component
title: Background task
status: stable
groma:
  id: background-task
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/application/background_task.py
description: Kör tidskrävande arbete i trådpoolen och levererar resultatet till GUI-tråden.
---

En liten byggsten som vyerna använder för att flytta arbete som modelladdning, bilavkodning, export och datasetsparning bort från GUI-tråden. Arbetet körs som en QRunnable i Qt:s globala trådpool och rapporteras tillbaka via signalerna succeeded, failed och finished, som med köad anslutning når mottagaren i GUI-tråden. Ett undantag i arbetet blir ett felmeddelande i stället för en krasch i arbetstråden. Uppgiften har ingen förälder, så en vy som rivs medan arbetet pågår får sina anslutningar bortkopplade av Qt och trådpoolen väntar in arbetet vid avslut.

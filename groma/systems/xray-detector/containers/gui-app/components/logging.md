---
type: C4 Component
title: Logging
status: stable
groma:
  id: logging
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/infrastructure/logging.py
description: Tredjepartens loggrar in i app.log.
---

Ligger i infrastructure så detektorerna kan fånga rfdetr:s loggrar utan att importera application; med fångsten i application blev beroendet infrastructure till application cykliskt. rfdetr sätter propagate=False och egna stream-handlers vid import, så utan fångsten stannar dess rader i konsolen.

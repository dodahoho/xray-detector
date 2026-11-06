---
type: C4 Component
title: Inställningar och tema
status: stable
groma:
  id: settings-theme
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/settings_view.py
    - scanner: python
      file: xray_detector/ui/theme.py
  group: Användargränssnitt
description: Temaväljare (system/ljust/mörkt) och gemensamma inställningar.
---

Inställningsfliken med val av tema som applicerar Fusion-stil med ljus eller mörk QPalette; läget "System" följer operativsystemets färgschema i realtid. Temat persistas i QSettings och tillämpas vid start.

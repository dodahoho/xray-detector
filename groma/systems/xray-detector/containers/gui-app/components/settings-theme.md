---
type: C4 Component
title: Tema
status: stable
groma:
  id: settings-theme
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/theme.py
  group: Användargränssnitt
description: Temaval (system/ljust/mörkt) som gäller hela appen.
---

Applicerar Fusion-stil med ljus eller mörk QPalette; läget "System" följer operativsystemets färgschema i realtid. Temat persistas i QSettings (ui/theme) och tillämpas vid start. Det byts i inställningsfliken, som är gemensam för hela appen.

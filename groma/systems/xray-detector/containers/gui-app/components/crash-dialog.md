---
type: C4 Component
title: Kraschdialog
status: stable
groma:
  id: crash-dialog
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/crash_dialog.py
  group: Användargränssnitt
description: Global excepthook som loggar och visar ohanterade undantag.
---

ui/crash_dialog.py (TASK-16): installeras i app.py efter QApplication-start; loggar undantaget med traceback till xray-loggern (rotationsloggen), skriver till stderr och visar en kritisk QMessageBox med undantagsnamn, meddelande och traceback som detaljtext innan appen far fortsatta - ingen tyst krasch. Kraschhanteraren själv sväljer aldrig fel utan loggar.

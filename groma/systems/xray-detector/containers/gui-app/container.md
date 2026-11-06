---
type: C4 Container
title: GUI-applikation
status: stable
groma:
  id: gui-app
  parent: xray-detector
  technology: PySide6 (Qt 6), OpenCV, QSettings
description: Skrivbordsappen som visar strömmar, hanterar annotering, dataset och träningsparametrar.
---

PySide6-applikation (Qt 6) i en process. MainWindow bygger flikarna Detektion, Annotation, Dataset, Träning och Inställningar. Alla trådar (kameror, träningsbevakning) körs i QThread och inställningar persistas med QSettings (ini). Bestämmer själv CUDA/CPU via torch.cuda och startar Träningsprocessen vid träning.

---
type: C4 Component
title: Flow layout
status: stable
groma:
  id: flow-layout
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/flow_layout.py
description: Flödeslayout som radbryter korten i datasetvyn.
---

Lägger widgets efter varandra och börjar en ny rad när raden är full. Qt har inget flödeslayout, så korten skulle annars behöva fasta kolumner. Varje widget får sin sizeHint och radbryts mot layoutens bredd, vilket ger samma beteende vid alla fönsterbredder. Layouten låg tidigare i dataset_view.py.

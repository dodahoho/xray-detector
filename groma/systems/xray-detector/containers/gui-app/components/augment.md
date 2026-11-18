---
type: C4 Component
title: Augment
status: stable
groma:
  id: augment
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/infrastructure/dataset_store/augment.py
description: Syntetiska variationer av datasetets bilder.
---

En plan räknas först fram med en lista av variationer per syntetisk bild och appliceras sedan på varje bild i bildparet, så vänster- och högerbilden får samma rotation, vändning, storlek och färg. Annoteringarna flyttas med samma matris som bilden, så rutorna ligger kvar på objekten. Rotation och storlek ändrar bildens mått i stället för att klippa bort innehåll, och ytan utanför en roterad bild blir vit som röntgenbildernas bakgrund.

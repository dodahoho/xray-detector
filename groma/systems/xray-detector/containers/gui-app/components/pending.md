---
type: C4 Component
title: Pending-kö
status: stable
groma:
  id: pending
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/infrastructure/dataset_store/pending.py
description: Kraschsäker kö på disk för fångster som ännu inte annoterats.
---

När operatören trycker Fånga sparas råbilderna och detektionerna under datakatalogens pending/ innan annoteringsvyn öppnas. Kraschar appen under annoteringen går fångsten inte förlorad: gruppen listas i datasetvyn vid nästa start och kan annoteras klart eller raderas. Först när annoteringen sparats till datasetet tas pending-gruppen bort.

---
type: C4 Component
title: Atomisk JSON-skrivning
status: stable
groma:
  id: json-io
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/infrastructure/dataset_store/json_io.py
      symbol: atomic_write_json
description: Atomisk JSON-skrivning som överlever en krasch mitt i skrivningen.
---

atomic_write_json skriver till en temporär fil i samma katalog, synkar till disk och byter ut målet med os.replace(), som är atomärt på samma volym. En krasch mitt i skrivningen lämnar därför antingen den gamla eller den nya kompletta filen, aldrig en halv dataset.json. Används av datasetlagringen och av pending-kön.

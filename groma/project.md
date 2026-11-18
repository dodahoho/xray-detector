---
type: Groma Project
title: xray-detector
groma:
  profile: architecture
description: Skrivbordsapp för röntgendetektion med annotering och modellträning.
---

Repo innehåller systemet X-ray detector (samma namn): en PySide6-GUI och en tillhörande tränings-CLI som körs som subprocess. Källkoden i xray_detector/ är lagerindelad i domain, application, infrastructure och ui, med testerna i tests/. Dokumentationen ligger i README.md (snabbstart) och docs/ (arkitektur och beteende).

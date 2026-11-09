---
id: TASK-12
title: Kraschsäker pending-kö på disk vid bildfångst
status: Done
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-09T13:32:00Z'
labels:
  - robusthet
  - dataset
  - annotation
dependencies: []
references:
  - dataset
  - annotation-view
  - dataset-view
modified_files:
  - xray_detector/infrastructure/dataset_store/pending.py
  - xray_detector/application/dataset_service.py
  - xray_detector/ui/main_window.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/dataset_view.py
  - tests/test_pending.py
priority: medium
type: feature
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
opencode-deepseek-flash sparar råbilder och detektioner direkt till disk (data/pending/groupId/) så fort användaren trycker Fånga, innan annoteringsvyn öppnas. Kraschar appen under annotering går fångsten inte förlorad; filerna rensas först när annoteringen committats. Se jämförelse_argon.md avsnitt 6 och jämförelse_qwen38.md.

I vibe-glm53: skriv fångsten till pending-katalogen i MainWindow._on_capture (eller camera_service), visa osparade pending-fångster i datasetvyn vid uppstart så de kan annoteras klart eller raderas.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 fångst skrivs till disk innan annoteringsvyn öppnas
- [x] #2 omstart efter krasch visar osparade fångster som kan annoteras eller raderas
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ny pending-kn i infrastructure/dataset_store/pending.py: nar operatoren trycker Fanga skrivs ramarna (PNG) och detektionerna till datakatalogens pending/<tidsstampel-grupp-id>/ med atomar indexfil FORE annoteringensvyn oppnas (MainWindow._on_capture). Kraschar appen under annoteringen finns fangsten kvar; datasetvyn visar en 'Osparade fangster'-sektion (streckad ram, OSPARAD-badges) dar gruppen kan dubbelklickas for att annoteras klart (ateroppning behaller grupp-id utan dubbelkopia) eller markeras och raderas med bekratelsedialog. Forsran nar annoteringen sparats (dataset commit) tar AnnotationView bort pending-gruppen; avbryt behaller den. Trasiga/korrupta pending-index hoppar over. Verifierat: 4 nya tester inklusive full karsh-simulering (fanga -> avbryt -> omstart i ny MainWindow -> listad OSPARAD -> dubbelklick -> spara -> pending borta + data i datasetet) samt radering fran vyn; hel svit 77 passed.
<!-- SECTION:FINAL_SUMMARY:END -->

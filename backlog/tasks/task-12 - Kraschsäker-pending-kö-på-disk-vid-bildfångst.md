---
id: TASK-12
title: Kraschsäker pending-kö på disk vid bildfångst
status: To Do
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - robusthet
  - dataset
  - annotation
dependencies: []
references:
  - dataset
  - annotation-view
  - dataset-view
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
- [ ] #1 fångst skrivs till disk innan annoteringsvyn öppnas
- [ ] #2 omstart efter krasch visar osparade fångster som kan annoteras eller raderas
<!-- AC:END -->

---
id: TASK-14
title: 'Annoterings-UX: zoom/pan, osparade ändringar och negativa exempel'
status: To Do
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - annotation
  - gui
  - ux
dependencies: []
references:
  - annotation-view
priority: medium
type: enhancement
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tre förbättringar från opencode-bigpickle och opencode-deepseek-flash (jämförelse_argon.md avsnitt 5:5):

1. Zoom med Ctrl+rull, panorering med mittenmusknapp, skaloberoende (kosmetiska) linjer och handtag så boxar är lätta att hantera oavsett zoomnivå.
2. Varning om man byter vy eller stänger med osparade annoteringsändringar.
3. Fråga om man vill spara som negativt exempel (bild utan objekt) om man klickar Spara utan inritade boxar, så blir negativa bilder användbara vid träning.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 annotering stöder zoom och pan med skaloberoende linjer och handtag
- [ ] #2 osparade ändringar ger varning innan vybyte/stängning
- [ ] #3 Spara utan boxar erbjuder att spara bilden som negativt exempel
<!-- AC:END -->

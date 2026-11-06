---
id: TASK-21
title: Utvärdera QGraphicsScene-baserad annoteringscanvas (spike)
status: To Do
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-06T14:07:00Z'
labels:
  - annotation
  - arkitektur
  - spike
dependencies: []
references:
  - annotation-view
priority: low
type: spike
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
opencode-deepseek-flash har implementerat annoteringen på QGraphicsScene/QGraphicsView i stället för en handmålad QWidget-canvas: gratis selektion/flytt/resize, skaloberoende kosmetiska pennor och inbyggd zoom/pan, mindre egen kod att underhålla.

Se jämförelse_glm53.md punkt 3. Eftersom vibe-glm53:s handritade canvas nyss byggts ut (markörer, Delete-tangent, tjockare linjer) är detta ett framtida alternativ: utvärdera kostnad/nytta att porta AnnotationCanvas till en BoxItem(QGraphicsRectItem)-modell i stil med deepseeks annotation_scene.py, skriv ner rekommendation i en decision-dokument.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 en utvärdering med prototyp och skriftlig rekommendation (portja eller behålla)
<!-- AC:END -->

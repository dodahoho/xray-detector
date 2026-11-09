---
id: TASK-21
title: Utvärdera QGraphicsScene-baserad annoteringscanvas (spike)
status: Done
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-09T13:40:00Z'
labels:
  - annotation
  - arkitektur
  - spike
dependencies: []
references:
  - annotation-view
modified_files:
  - tests/prototype/annotation_scene.py
  - tests/prototype/test_prototype_annotation_scene.py
  - docs/decision-annotation-canvas.md
priority: medium
type: enhancement
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
opencode-deepseek-flash har implementerat annoteringen på QGraphicsScene/QGraphicsView i stället för en handmålad QWidget-canvas: gratis selektion/flytt/resize, skaloberoende kosmetiska pennor och inbyggd zoom/pan, mindre egen kod att underhålla.

Se jämförelse_glm53.md punkt 3. Eftersom vibe-glm53:s handritade canvas nyss byggts ut (markörer, Delete-tangent, tjockare linjer) är detta ett framtida alternativ: utvärdera kostnad/nytta att porta AnnotationCanvas till en BoxItem(QGraphicsRectItem)-modell i stil med deepseeks annotation_scene.py, skriv ner rekommendation i en decision-dokument.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 en utvärdering med prototyp och skriftlig rekommendation (portja eller behålla)
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Spike levererad i tv delar: (1) korbar prototyp tests/prototype/annotation_scene.py - BoxItem (QGraphicsRectItem) med 8 storleksandring-handtag, min-storlek, kosmetisk penna (konstant skarmtjocklek over zoom), AnnotationScene med bildunderlag och AnnotationView med pekcentrerad Ctrl+musjul-zoom, plus 6 tester som visar gratis selektion/flytt, penn-invarians vid 6x zoom, handtags-resize i bildkoordinater, min-storleksregeln, annoteringsexport och att vy-zoom inte pavrattar scendata. (2) Skriftlig rekommendation i docs/decision-annotation-canvas.md: behall dagens handmalade canvas kort sikt (den ar nyligen utbyggd och helt testad; porten kostar 1-2 dagar inklusive omskrivning av 16 GUI-tester), men planera en port nar zoom-/narhetskrav vaxer eller nast staor annoteringsfunktion - QGraphicsScene ar ratt slutmal eftersom kosmetiska pennor och gratis zoom/pan tar bort den egna matematiken. Triggerpunkter och nast-steg for en framtida port upptecknade.
<!-- SECTION:FINAL_SUMMARY:END -->

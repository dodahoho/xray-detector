---
id: TASK-164
title: Annotering och Detektion - Möjlighet att maximera en bildkälla
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-19T09:38:00Z'
updated_date: '2026-11-20T13:49:00Z'
labels: []
dependencies: []
references:
  - xray_detector/ui/panel_split.py
modified_files:
  - xray_detector/ui/style.py
  - xray_detector/ui/tool_icons.py
  - xray_detector/ui/panel_split.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/stream_panel.py
  - xray_detector/ui/detection_view.py
  - tests/test_tool_icons.py
  - tests/test_panel_split.py
  - docs/beteende.md
type: feature
ordinal: 300000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ibland kan behovet att se ena bildkällans fönster större. Det vore bra att kunna maximera ena visningen samtidigt som den andra bildkällan minimeras och tvärtom.

Kanske till och med göra ramen i mitten justerbar så att man kan justera storlekarna på fönstrena dynamiskt? OBS! Överväg endast dynamisk storleksändring av bildramarna om det är en relativt okomplicerad ändring jämfört med att maximera/minimera. Annars är det bättre att hålla sig till att endast maximera/minimera de olika bildfönstrena.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Varje bildpanel i annoterings- och detektionsvyn har en knapp som maximerar panelen och fäller ihop den andra.
- [ ] #2 Knappen på den maximerade panelen visar båda bilderna igen, med samma storlekar som före maximeringen.
- [ ] #3 Ramen mellan de två panelerna går att dra för att ändra storlekarna dynamiskt.
- [ ] #4 Ett nytt bildpar i annoteringsvyn börjar med båda bilderna synliga.
- [ ] #5 docs/beteende.md beskriver maximeringen och den justerbara ramen.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Ny modul xray_detector/ui/panel_split.py med PanelSplit, en QSplitter som håller de två bildpanelerna, ger en justerbar mittram och en maximera-knapp per panel som fäller ihop den andra panelen.
2. Ikoner för maximera och återställ i ui/tool_icons.py, ritade med QPainter som pennan och handen.
3. Annoteringsvyn: AnnotationView lägger canvasarna i en PanelSplit i stället för en QHBoxLayout, och ZoomOverlay får en maximera-knapp.
4. Detektionsvyn: DetectionView lägger strömpanelerna i en PanelSplit, och StreamPanel får en maximera-knapp i raden ovanför bilden.
5. load_captures återställer båda bilderna, så ett nytt bildpar alltid börjar med två synliga bilder.
6. Tester i tests/test_panel_split.py och uppdatering av docs/beteende.md.
<!-- SECTION:PLAN:END -->

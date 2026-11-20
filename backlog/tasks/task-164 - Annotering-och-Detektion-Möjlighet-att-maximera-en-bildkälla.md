---
id: TASK-164
title: Annotering och Detektion - Möjlighet att maximera en bildkälla
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-19T09:38:00Z'
updated_date: '2026-11-20T13:51:00Z'
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
- [x] #1 Varje bildpanel i annoterings- och detektionsvyn har en knapp som maximerar panelen och fäller ihop den andra.
- [x] #2 Knappen på den maximerade panelen visar båda bilderna igen, med samma storlekar som före maximeringen.
- [x] #3 Ramen mellan de två panelerna går att dra för att ändra storlekarna dynamiskt.
- [x] #4 Ett nytt bildpar i annoteringsvyn börjar med båda bilderna synliga.
- [x] #5 docs/beteende.md beskriver maximeringen och den justerbara ramen.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Den gemensamma ytan ligger i `xray_detector/ui/panel_split.py`. `PanelSplit` är en QSplitter med `setChildrenCollapsible(False)`, så ramen bara går att dra så långt att båda panelerna syns, och en maximering gömmer den andra panelen i stället för att dra ramen till kanten. Storlekarna sparas före maximeringen och sätts tillbaka vid återställning, så en storlek man dragit fram inte tappas.

Maximera-knappen ligger först i panelens egen rad: i `ZoomOverlay` för annoteringsvyn och i `StreamPanel`s rad ovanför bilden för detektionsvyn. Ikonerna `maximize_icon()` och `restore_icon()` ritas som streckade rutor i `ui/tool_icons.py`, i samma stil som pennan och handen, och knappen byter ikon och verktygstips när panelen är maximerad.

Verifiering: `uv run ruff check xray_detector tests` rent. `uv run pytest -q -n auto --ignore=tests/test_shortcuts.py` gav 1012 passed, 1 skipped; `uv run pytest tests/test_shortcuts.py -q` gav 32 passed. `tests/test_shortcuts.py` är flaky under pytest-xdist (tre olika test fallerar från körning till körning); samma flakiness finns på orörd kod med ändringarna stashade, så den hör inte till den här uppgiften.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
De två bildpanelerna i annoterings- och detektionsvyn delar nu ytan med en QSplitter i stället för en QHBoxLayout. Ramen i mitten går att dra, så storlekarna ändras dynamiskt, och först i varje panels egen rad sitter en maximera-knapp som fäller ihop den andra panelen. Ett klick till visar båda igen med samma storlekar som före maximeringen. Ramen kan inte dras ihop till noll, så en bild aldrig försvinner, och ett nytt bildpar i annoteringsvyn börjar alltid med båda bilderna synliga.

Den gemensamma ytan ligger i `xray_detector/ui/panel_split.py` och används av båda vyerna. Ikonerna för maximera och återställ ritas med QPainter i `ui/tool_icons.py`, så de följer paletten och behöver ingen bildfil. `docs/beteende.md` beskriver knappen och den justerbara ramen i både Detektion- och Annotation-avsnittet.

Verifierat med `tests/test_panel_split.py` (13 tester) och `tests/test_tool_icons.py`, plus hela sviten: 1012 passed och 1 skipped parallellt, 32 passed för `tests/test_shortcuts.py` seriellt, och ruff rent. `tests/test_shortcuts.py` är flaky under pytest-xdist även på orörd kod, så den körningen bör hållas seriell i CI.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-66
title: Dataset - titel och innehåll i card
status: Done
assignee:
  - '@vibe-mistral'
created_date: '2026-11-12T14:28:00Z'
updated_date: '2026-11-12T14:47:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 64000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Titeln ska bara ha tid samt en uppräkning av alla objektklasser som bilderna innehåller (utan antal). Uppräkningen av objektklasser görs med badges efter varandra.

Den uppräkning som nu finns under respektive thumbnail i ett card kan tas bort. Endast titelrad och thumbnails i ett card
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Titelraden visar fångstens tid
- [x] #2 Titelraden visar en badge per objektklass i fångsten, utan antal
- [x] #3 Ingen uppräkning av klasser under respektive thumbnail i kortet
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
1. Gör rubrikraden till en rad med tidsetikett och en badge per objektklass, färgad med klassens färg.
2. Låt rubrikraden bära färg och bakgrund så markeringen täcker både tid och märken, och behåll breddreservationen för ' · Markerad'.
3. Ta bort bildtexten under thumbnails; osparade fångsters käll-etikett flyttas till en tooltip.
4. Test: titelraden visar tid och en badge per klass utan antal, och inga bildtexter finns kvar i kortet.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rubriken är nu en rad (QFrame med objectName captureHeader) med tidsetiketten och en badge per klass; raden bär färg och bakgrund så markeringen täcker både tid och märken, och tidsetiketten behåller breddreservationen för " · Markerad" så korten inte flyttas. Badgen använder class_color med mörk eller ljus text efter färgens ljushet. Bildtexten under thumbnails är borta; osparade fångsters käll-etikett och antal detektioner ligger i en tooltip i stället. Två stilmissar rättade på vägen: kortets QFrame-selektor gav rubrikraden och tidsetiketten samma ram (QLabel ärver QFrame), och rubrikens stil är nu scopad till objectName respektive CaptureCard.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Titelraden visar fångstens tid och en badge per objektklass; bildtexterna under thumbnails är borta.

Vad som ändrades i xray_detector/ui/dataset_view.py:
- _capture_header bygger en rubrikrad med tidsetiketten och en badge per klass, färgad med class_color och med mörk eller ljus text efter färgens ljushet.
- Rubrikraden bär färg och bakgrund, så markeringen täcker både tid och märken; tidsetiketten reserverar fortfarande bredden för " · Markerad".
- Kortets titel är bara tiden (sparade fångster) respektive "Osparad · tid" (osparade), utan antal bilder eller objekt.
- Thumbnail har ingen bildtext längre; osparade fångsters käll-etikett och antal detektioner ligger i en tooltip.
- Kortets och rubrikens stilar är scopade till CaptureCard respektive objectName, eftersom QLabel ärver QFrame och annars fick kortets ram.

Verifiering:
- Nya och uppdaterade tester i tests/test_dataset_header.py: titelraden är exakt "09:56:38", märkena är ["09:56:38", "kniv", "pistol"] utan antal, och kortet innehåller bara titelrad och thumbnails.
- tests/test_dataset_selection.py och tests/test_pending.py uppdaterade för rubrikraden respektive tooltipen.
- Hela sviten: 452 passed, 1 skipped.
- Renderad vy före och efter markering: tid i grått, klassmärken i klassfärg, ingen bildtext, och den markerade raden fylls med accentfärg över hela bredden.
- ruff check på ändrade filer: inga anmärkningar.

Risker: en fångst med många klasser får en rad märken som kan bli bredare än kortet; raden radbryts inte.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-163
title: Annotering - Zooma i bild
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-19T09:30:00Z'
updated_date: '2026-11-19T18:15:00Z'
labels: []
dependencies: []
type: feature
ordinal: 308000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Om man ska annotera små objekt så finns behov av att kunna zooma i bilden. Lägg in zoom i annoteringsläget i övre vänstra hörnet av respektive bild med en snabbknapp för att återgå till 100%
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Varje bild i annoteringsläget har en zoompanel i övre vänstra hörnet.
- [x] #2 Panelens − och + zoomar bilden och siffran mellan dem visar aktuell nivå i procent.
- [x] #3 En knapp i panelen återgår till 100 % och centrerar bilden.
- [x] #4 Nivån följer även Ctrl+hjul och nollställs när en ny bild laddas.
- [x] #5 docs/beteende.md beskriver zoompanelen.
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
1. Lägg en ZoomOverlay som barnwidget till AnnotationCanvas, placerad i bildens övre vänstra hörn och flyttad i resizeEvent.
2. Panelen innehåller −, aktuell zoom i procent, + och en 100 %-knapp som återgår till 100 % och centrerar bilden.
3. Koppla knapparna till canvasens zoom in/ut/reset; etiketten uppdateras vid knapptryck, Ctrl+hjul och när en ny bild laddas.
4. Uppdatera docs/beteende.md.
5. Tester för panelens placering, knapparna, etiketten, klämning och nollställning vid ny bild; kör pytest och ruff.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifiering:
- AC1: ZoomOverlay skapas som barnwidget till varje AnnotationCanvas och placeras på (8, 8) i resizeEvent. test_annotation_zoom.py::test_the_zoom_panel_sits_in_the_top_left_corner och test_each_image_in_the_annotation_view_has_its_own_zoom_panel kontrollerar placeringen och att de två bilderna har varsin panel; test_the_panel_stays_in_the_corner_when_the_canvas_is_resized och test_the_panel_is_hidden_until_an_image_is_loaded täcker omflyttningen och läget utan bild.
- AC2: − och + anropar canvasens zoom_out/zoom_in, som zoomar kring bildens mitt med stegen 0.8 och 1.25. Etiketten visar round(zoom * 100) %. test_the_buttons_zoom_in_and_out_and_update_the_label, test_the_buttons_zoom_around_the_image_center och test_the_buttons_respect_the_zoom_limits (20 %–500 %) verifierar det.
- AC3: 100 %-knappen anropar reset_view, som sätter zoom 1.0 och pan (0, 0). test_the_reset_button_returns_to_100_percent_and_centers_the_image kontrollerar zoom, pan, bildens origo och etiketten.
- AC4: zoom_at uppdaterar etiketten, så Ctrl+hjul följer med (test_the_label_follows_ctrl_wheel), och load_frame nollställer zoom och etikett (test_a_new_frame_starts_at_100_percent).
- AC5: docs/beteende.md beskriver panelen, knapparna, Ctrl+hjul och panoreringen med mittenknappen.

Tester: uv run pytest -q -p no:xdist gav 990 passed, 1 skipped. uv run ruff check . går igenom. Panelen renderades också manuellt till en bild och lästes av: 213x40 px i (8, 8) med etiketten 125 % efter ett klick på +.

Noteringar:
- Knapparna använder den gemensamma knapphöjden (32 px) enligt test_style.py, så panelen blir 40 px hög inklusive marginaler.
- Panelen ligger i canvasens hörn, inte i bildens letterboxade hörn, så den står still när bilden panoreras eller zoomas.
- Bakgrundsfärgen ligger i ui/colors.py som ZOOM_PANEL_BACKGROUND, eftersom test_colors.py förbjuder hårdkodade färger utanför den filen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Annoteringsvyn har fått en zoompanel i varje bilds övre vänstra hörn: − och + zoomar kring bildens mitt, siffran mellan dem visar nivån i procent och 100 % återgår till 100 % och centrerar bilden. Panelen ligger ovanpå bilden med halvtransparent bakgrund, så den syns mot både ljusa och mörka bilder, och den följer med när vyn storleksändras. Nivån uppdateras även när man zoomar med Ctrl+hjul och nollställs när en ny bild laddas. Verifierat med uv run pytest -q -p no:xdist (990 passed, 1 skipped) och uv run ruff check . (inga anmärkningar), plus en manuell rendering av panelen. Panelen ligger i canvasens hörn i stället för i bildens letterboxade hörn, så den står still när bilden panoreras eller zoomas.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-168
title: Annotering - Växla läge mellan rita och panorera vid inzoomad bild
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-20T11:08:00Z'
updated_date: '2026-11-20T11:48:00Z'
labels: []
dependencies: []
references:
  - annotation-view
modified_files:
  - xray_detector/ui/annotation_view.py
  - tests/test_annotation_pan.py
  - docs/beteende.md
type: feature
ordinal: 304000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När en bild zoomas in måste man kunna panorera i bildytan så man väljer vilken del av den inzoomade bilden som är synlig. 

Förslag: när bild är zoomad så att hela bilden inte ryms i ytan så finns ikoner för rita (default vald) och panorera. Vid klick på panorera gör ett klick och dra på bildytan att synliga delen av bilden flyttas. Vid klick på rita återgår man till standardläge att klicka och dra ritar upp en box för att annotera detekterat objekt.

Panoreringsläge är endast relevant om bilden inte ryms i den tillgängliga ytan för att visa bilden.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Zoompanelen visar verktygen Rita och Panorera när bilden är så inzoomad att hela bilden inte ryms i ytan.
- [x] #2 Rita är valt från början och ett klick och drag i bildytan ritar en ny annotering som förut.
- [x] #3 I panorera-läget flyttar ett klick och drag i bildytan den synliga delen av bilden i stället för att rita.
- [x] #4 Verktygsvalet döljs och läget går tillbaka till Rita när hela bilden ryms i ytan igen.
- [x] #5 docs/beteende.md beskriver verktygsvalet.
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
1. Lägg verktygsläget (rita/panorera) i AnnotationCanvas och en _fits()-kontroll som säger om hela bilden ryms i ytan på aktuell zoomnivå.
2. Lägg två checkbara knappar, Rita och Panorera, i ZoomOverlay med en exklusiv QButtonGroup; de syns bara när bilden inte ryms.
3. Låt vänsterdrag panorerar i panorera-läget, behåll mittenknappens panorering, och visa öppen hand som pekare.
4. Uppdatera verktygets tillgänglighet vid zoom, återställning, storleksändring och ny bild; panorera faller tillbaka på rita när bilden ryms.
5. Uppdatera docs/beteende.md.
6. Tester i tests/test_annotation_pan.py för synlighet, standardläge, panorering, ritning efter byte, pekare och återgång; kör pytest och ruff.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifiering:
- AC1: ZoomOverlay har två checkbara knappar, Rita och Panorera, i en exklusiv QButtonGroup. set_tool_available visar dem bara när _fits() är falskt, alltså när bildens skalade mått är större än canvasens. test_the_tool_buttons_are_hidden_while_the_whole_image_fits (100 %) och test_the_tool_buttons_appear_when_the_image_no_longer_fits (125 %) täcker båda lägena, och test_the_panel_shrinks_when_the_tool_buttons_are_hidden visar att panelen växer från 213 till 383 px när knapparna dyker upp.
- AC2: _tool är TOOL_DRAW från konstruktionen och draw_button är förvald. test_draw_is_the_default_tool kontrollerar läget, test_draw_mode_draws_again_after_switching_back att ett drag efter ett byte tillbaka till Rita skapar en ruta och markerar canvasen ändrad; test_annotation_canvas.py::test_draw_creates_rect_with_class är oförändrat grön.
- AC3: I panorera-läget tar mousePressEvent vänsterknappen före träffkontrollerna och sätter _mode = pan, så mouseMoveEvent flyttar _pan i stället för att rita, flytta eller välja. test_pan_mode_moves_the_visible_part_of_the_image visar att bildens origo flyttas (-50, -30) för ett drag på samma avstånd, test_pan_mode_does_not_draw_a_box att inga rutor skapas och canvasen inte blir ändrad, test_pan_mode_does_not_move_or_select_an_annotation att en ruta under pekaren ligger still, test_pan_mode_does_not_open_the_class_dialog att klassdialogen inte öppnas och test_the_cursor_shows_the_open_hand_in_pan_mode att pekaren blir en öppen hand.
- AC4: _update_tool_availability körs vid zoom, återställning, storleksändring och ny bild och faller tillbaka på Rita när bilden ryms. test_the_tool_returns_to_draw_when_the_image_fits_again (100 %-knappen), test_pan_mode_is_refused_while_the_whole_image_fits (set_tool avvisas), test_a_new_frame_starts_in_draw_mode och test_an_empty_canvas_keeps_no_tool_from_the_previous_pair täcker återgången.
- AC5: docs/beteende.md beskriver verktygen i punkten om Annotation.

Tester: uv run pytest -q -p no:xdist gav 1019 passed, 1 skipped (350,76 s). uv run ruff check . går igenom utan anmärkningar. Panelen renderades också manuellt: 213x40 px vid 100 % med verktygen dolda, 383x40 px vid 125 % med Rita och Panorera synliga och Rita vald, och efter ett klick på Panorera är den knappen vald och pekaren en öppen hand.

Noteringar:
- Verktygen är textknappar (Rita, Panorera) i samma halvtransparenta panel som zoomkontrollerna, i linje med vyernas övriga knappar, i stället för ritade ikoner.
- _fits() jämför bildens skalade mått med canvasens mått, så regeln följer beskrivningen att panorering bara är relevant när bilden inte ryms, i stället för att bara titta på zoomnivån.
- Mittenknappens panorering finns kvar och fungerar i båda lägena (test_the_middle_button_still_pans_in_draw_mode).
- load_captures återställer en canvas som inte får någon bild med reset_view(), så zoom och verktyg inte ligger kvar från föregående bildpar.
- Pan-offseten kläms inte, så bilden kan dras ur vyn; 100 %-knappen tar tillbaka den. Samma beteende som mittenknappen hade före uppgiften.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Annoteringsvyns zoompanel har fått två verktyg: Rita, som är valt från början och ritar en box vid klick och drag, och Panorera, där samma drag flyttar den synliga delen av den inzoomade bilden och pekaren blir en öppen hand. Verktygen syns bara när bilden är så inzoomad att hela bilden inte ryms i ytan; när bilden ryms igen döljs de och läget går tillbaka till Rita. Mittenknappens panorering finns kvar i båda lägena, och en canvas som inte får någon bild nollställs så zoom och verktyg inte ligger kvar från föregående bildpar. Verifierat med uv run pytest -q -p no:xdist (1019 passed, 1 skipped) och uv run ruff check . (inga anmärkningar), plus en manuell rendering av panelen i båda lägena. Pan-offseten kläms inte, så bilden kan dras ur vyn; 100 %-knappen tar tillbaka den, samma beteende som mittenknappen hade före uppgiften.
<!-- SECTION:FINAL_SUMMARY:END -->

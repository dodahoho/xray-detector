---
id: TASK-169
title: Annotering - Ctrl+drag panorerar och ikoner på verktygsknapparna
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-20T11:58:00Z'
updated_date: '2026-11-20T12:07:00Z'
labels: []
dependencies: []
references:
  - annotation-view
modified_files:
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/colors.py
  - xray_detector/ui/tool_icons.py
  - tests/test_annotation_pan.py
  - tests/test_tool_icons.py
  - docs/beteende.md
type: feature
ordinal: 305000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Uppföljning på TASK-168. Panoreringen ska gå snabbt att komma åt utan att först klicka på verktyget: så länge Ctrl hålls intryckt flyttar ett klick och drag i bildytan den inzoomade bilden, och när Ctrl släpps gäller det valda verktyget igen. Ctrl+scroll fortsätter att zooma som förut. Verktygsknapparna i zoompanelen ska visa ikoner i stället för texten "Rita" och "Panorera".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Så länge Ctrl hålls intryckt flyttar ett klick och drag i bildytan den inzoomade bilden, oavsett vilket verktyg som är valt.
- [ ] #2 När Ctrl släpps gäller det valda verktyget igen, och Ctrl+scroll zoomar fortfarande som förut.
- [ ] #3 Pekaren visar en öppen hand när Ctrl hålls intryckt över bilden.
- [ ] #4 Verktygsknapparna visar ikoner för rita och panorera i stället för text, med kvarvarande verktygstips.
- [ ] #5 docs/beteende.md beskriver Ctrl+drag och ikonerna.
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
1. Låt mousePressEvent ta vänsterknappen som panoreringsdrag även när Ctrl är intryckt, oavsett valt verktyg, och låt _hover_cursor visa öppen hand så länge Ctrl hålls.
2. Skicka händelsens modifiers till _hover_cursor från press-, move- och release-hanteringen, så pekaren följer Ctrl utan extra tillstånd.
3. Ny modul xray_detector/ui/tool_icons.py med draw_icon() och pan_icon() ritade med QPainter, i samma stil som temaväxlarens ikoner.
4. Byt knapparnas text mot ikoner i ZoomOverlay, med kvarvarande verktygstips och tillgängliga namn.
5. Uppdatera docs/beteende.md.
6. Tester för Ctrl+drag, att Ctrl+scroll fortfarande zoomar, pekaren och att knapparna har ikoner; kör pytest och ruff samt renderar panelen.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifiering:
- AC1: mousePressEvent tar vänsterknappen som panoreringsdrag när Ctrl är intryckt, före träffkontrollerna, så inget ritas, flyttas eller väljs. test_ctrl_drag_pans_while_ctrl_is_held visar att bildens origo flyttas (-50, -30) för ett drag på samma avstånd med rita valt, test_ctrl_drag_pans_even_when_the_pan_tool_is_selected att det gäller även med panorera valt, test_ctrl_drag_does_not_draw_a_box att inga rutor skapas och canvasen inte blir ändrad, och test_ctrl_drag_keeps_the_selected_tool att _tool och den valda knappen ligger kvar.
- AC2: Ctrl ändrar aldrig _tool, så det valda verktyget gäller direkt när tangenten släpps; test_drawing_works_again_when_ctrl_is_released ritar en ruta efter ett Ctrl+drag. test_ctrl_wheel_still_zooms_and_does_not_pan visar att Ctrl+hjul fortfarande går genom zoom_at (1.0 -> 1.25) och flyttar bilden, och den manuella körningen gav 1.25 -> 1.5625.
- AC3: _hover_cursor tar emot händelsens modifiers och returnerar öppen hand så länge Ctrl hålls. test_the_cursor_shows_the_open_hand_while_ctrl_is_held täcker hover, och mouseReleaseEvent använder samma anrop så handen syns även efter draget medan Ctrl hålls.
- AC4: Knapparna har tom text, en QIcon och kvarvarande verktygstips och tillgängliga namn. test_the_tool_buttons_show_icons_instead_of_text kontrollerar text, ikon, accessibleName och tooltip; tests/test_tool_icons.py kontrollerar storlek, att penna och hand är olika former, att de använder TOOL_ICON_COLOR och att hörnen är genomskinliga. Panelen krympte från 383 till 277 px vid 125 %.
- AC5: docs/beteende.md beskriver Ctrl+drag i punkten om Annotation och i tangentbordsöversikten.

Tester: uv run pytest -q -p no:xdist gav 1031 passed, 1 skipped (364,16 s). uv run ruff check . går igenom utan anmärkningar. Panelen renderades manuellt: 277x40 px vid 125 %, med pennan vit på den blå valda knappen och handen grå på den ovalda. Ett Ctrl+drag flyttade bilden (-50, -30) utan att rita något och med rita kvar som verktyg, och Ctrl+hjul ändrade zoomnivån 1.25 -> 1.5625.

Noteringar:
- Ikonerna ritas med QPainter i ui/tool_icons.py och finns i två varianter: grå för den ovalda knappen och ljus för den valda, så pennan syns mot den blå bakgrunden. Qt byter variant själv via QIcon.State.
- Ctrl är ett tillfälligt lån av panoreringen: _tool ändras inte, så det valda verktyget gäller direkt när tangenten släpps.
- Ctrl+drag panorerar även när hela bilden ryms, som mittenknappen redan gjorde; 100 %-knappen centrerar bilden igen.
- Nya filen xray_detector/ui/tool_icons.py har ingen ägare i groma-arkitekturen än ("no enabled scanner reads it"); den hör till komponenten annotation-view, som referensen pekar på.
<!-- SECTION:NOTES:END -->

---
id: TASK-71
title: Annotering - Hantering av objektklasser
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T19:52:00Z'
updated_date: '2026-11-12T20:06:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 69000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
* Default (vid nyinstallation) av applikationen ska inga objektklasser finnas i annoteringslistan.
* Om det vid växling till annotationsvy är inte finns några definierade objektklasser ska användaren få en fråga om man vill lägga till objektklasserna från modellens lista (namnges inte individuellt i dialogrutan, men antal klasser det rör sig om kan tas med)
* Om det vid växling till annotationsvy finns definierade objektklasser, men aktuellt bildpar har detekterat ett objekt av klass som inte finns i annoteringslistan ska användaren få en fråga om man vill lägga till aktuell objektklass (namnet tas med i dialogrutan)
* Annoteringslistans klasser är detsamma som objektklasserna i applikationens dataset
* Vid klick på texten för objektklass i en befintlig annotering i bilden öppnas en dialog med dropdown/select där objektklass kan bytas
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Annoteringslistan är tom vid nyinstallation; varken modellens klasser eller config.classes fyller den automatiskt.
- [x] #2 När vyn öppnas utan definierade objektklasser frågar appen om modellens klasser ska läggas till, med antalet klasser i dialogen och utan att namnge dem.
- [x] #3 När bildparet detekterat en klass som saknas i annoteringslistan frågar appen om just den klassen, med klassnamnet i dialogen.
- [x] #4 Annoteringslistans klasser är datasetets objektklasser; tillägg och borttagningar skrivs till datasetet.
- [x] #5 Ett klick på klassnamnet för en annotering i bilden öppnar en dialog med dropdown där objektklassen kan bytas.
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
1. refresh_classes() bygger bara listan ur datasetet; ingen automatisk påfyllning från modellen eller config.classes (AC 1, 4).
2. load_captures() frågar om modellens klasser när listan är tom, med antalet klasser i dialogen (AC 2).
3. load_captures() frågar per klass som bildparet detekterat men listan saknar, med klassnamnet i dialogen (AC 3).
4. Klassnamnet i bilden blir klickbart: canvasen träffar etiketten och skickar en signal; vyn öppnar en dialog med dropdown där klassen kan bytas (AC 5).
5. Uppdatera tests/test_annotation_classes.py till det nya beteendet och lägg till tester för de nya flödena; kör hela sviten.
6. Uppdatera README (annotationsavsnittet och config.classes).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementation:
- refresh_classes() läser bara datasetets kategorier. _default_classes togs bort, så varken modellens klasser eller config.classes fyller listan automatiskt; en nyinstallation börjar tom.
- load_captures() frågar med QMessageBox.question i två steg: först om modellens klasser när listan är tom (antalet nämns, inte namnen), sedan per detekterad klass som saknas i listan (klassnamnet nämns). Ja skriver klasserna till datasetet med set_classes().
- AnnotationCanvas har en ny signal class_label_clicked. _label_rect() räknar ut textens träffyta med QFontMetrics från samma font och baslinje som drawText använder, så klickytan matchar den ritade texten. Vyn öppnar QInputDialog.getItem (dropdown, ej redigerbar) och byter klass med set_item_class(), som markerar canvasen som ändrad så Spara-knappen aktiveras.

Verifiering:
- Hela sviten: 484 passed, 1 skipped (tests/test_shortcuts.py::test_alt_letter_switches_tab var flaky i en körning och passerar både enskilt och i omkörning av hela sviten).
- Nya tester: tests/test_annotation_classes.py (26 st) och tests/test_annotation_canvas.py (10 st).
- Renderad canvas bekräftar att _label_rect (50,21,43,26 vid skala 2.5) täcker den ritade texten och att ytan ovanför är bild utan text.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Annoteringsvyns klasslista börjar nu tom och fylls bara på efter en fråga. refresh_classes() läser datasetets kategorier och _default_classes togs bort, så varken modellens klasser eller config.classes skrivs in automatiskt. När vyn öppnas frågar load_captures() först om modellens klasser när listan är tom (antalet nämns, inte namnen) och sedan per detekterad klass som listan saknar (klassnamnet nämns); ja skriver klasserna till datasetet med set_classes().

Klassnamnet ovanför en annotering är klickbart. Canvasen räknar ut textens träffyta med QFontMetrics från samma font och baslinje som drawText använder, skickar class_label_clicked och vyn öppnar QInputDialog.getItem med en dropdown över datasetets klasser. Bytet går via set_item_class(), som markerar canvasen som ändrad så Spara-knappen aktiveras.

Verifiering: hela sviten 484 passed, 1 skipped. Nya tester i tests/test_annotation_classes.py (26) och tests/test_annotation_canvas.py (10) täcker alla fem AC. En renderad canvas bekräftar att träffytan (50,21,43,26 vid skala 2.5) täcker den ritade texten. README är uppdaterad för det nya flödet och för att config.classes nu bara styr overlayfärgerna.

Risker: klassnamnet kläms fast på y=22 när annoteringen ligger högst upp i bilden, så etiketten kan då överlappa rektangeln och ta klicket före flytthanteraren. En detekterad klass som användaren väljer att inte lägga till behåller sitt namn på rektangeln och blir en datasetkategori först vid sparning.
<!-- SECTION:FINAL_SUMMARY:END -->

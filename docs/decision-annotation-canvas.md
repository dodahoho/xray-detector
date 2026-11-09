# Beslut: QGraphicsScene-baserad annoteringsduk (utvärdering, TASK-21)

Datum: 2026-11-09 · Status: utvärdering klar, rekommendation given · Prototyp: `tests/prototype/annotation_scene.py` (testad av `tests/prototype/test_prototype_annotation_scene.py`)

## Bakgrund

Annoteringsduken (`xray_detector/ui/annotation_view.py`, klassen `AnnotationCanvas`) är en handmålad QWidget: all markering, flytt, storleksändring, zoom, panorering och dirty-hantering är egen kod (~450 rader). Som jämförelse har opencode-deepseek-flash implementerat annoteringen på QGraphicsScene/QGraphicsView, med gratis selektion/flytt/zoom ur Qt och mindre egen kod att underhålla. Denna spike utvärderar om och när en port lönar sig.

## Prototypens resultat

Prototypen (`BoxItem(QGraphicsRectItem)`, `AnnotationScene`, `AnnotationView)`) demonstrerar:

- **Kosmetisk penna** (`pen.setCosmetic(True)`) ger konstant linjetjocklek på skärmen oavsett zoomnivå utan egen matte — verifierat i test.
- **Zoom/pan gratis**: `AnchorUnderMouse` + `scale()` ger pekcentrerad zoom (motsvarar vår handskrivna `zoom_at`) och mittenknappspanorering är inbyggd i QGraphicsView — ~0 rader egen kod.
- **Selektion/flytt är flaggor** (`ItemIsSelectable | ItemIsMovable`); vald stil sköts via `itemChange` — vår handkodade selected-state, flytt-läge och markörlogik försvinner.
- **Storleksändring kräver fortfarande egen kod** (8 handtag, min-storlek, träfftolerans skalinverterad) — Qt ger ingen resize-gratisfördel, men logiken blir renare när allt(skriver i scenkoordinater: `resize_to(handle, pos)` tar bildkoordinater direkt.
- **Bildunderlag**: `QGraphicsPixmapItem` ersätter vår handritade utskrift av QImage i `paintEvent`.

Motsvarande kod i produkten (canvas ~450 rader) ersätts i prototypen av ~180 rader inklusive handtagen.

## Skillnader mot dagens AnnotationCanvas

| Egenskap | Dagens canvas | QGraphicsScene-prototyp |
|---|---|---|
| Rita/flytta/storleksändra | helt egen kod | selektion+flytt gratis; resize egen men enklare |
| Zoom/pan (TASK-14) | egen zoom_at/pan-matematik | inbyggt (`AnchorUnderMouse`, skalning) |
| Konstant pennbredd vid zoom | kräver egen mot-skala | kosmetisk penna, 1 rad |
| Klassetiketter på rutorna | egen drawText i paintEvent | `QGraphicsSimpleTextItem` (item, skalbar) |
| Delete-tangent/tangenter | egen `keyPressEvent` | densamma (`keyPressEvent` på vyn) |
| Dirty-/sparmappning | `result()` konverterar QImage-pixlar till numpy | direkt: ruta i scenkoordinater -> bbox (protokoll-test) |
| Beroende på vår Zoom/pan-testsvit |Coverage | behöver omskrivning (~7 i test_annotation_canvas + 9 i test_annotation_ux) |

## Risker med port

1. Konverteringen av befintlig data kräver noggrannhet: vår `RectItem(x1,y1,x2,y2)`-konstruktor (två hörn) och QImage->numpy i `result()` ersätts av scenrektanglar direkt — ett gränssnitt byte som rör annoteringsvyns `load_captures`/`result()`.
2. Alla 16 GUI-tester för canvas/UX måste skrivas om mot scenens event-modell ( QTest på vy istället för widget).
3. Beteenden vi nyligen lagt (osparade-ändringar, negativa exempel, class-hantering) hänger på signalerna från canvasen och måste trådas om.
4. Kortsiktig avbrottstrippa i taget "snart klart"-flödet; porten bör göras som ett eget task med tydlig testplan.

## Rekommendation

**Behålla dagens handmålad canvas kort sikt; planera en port när zoom/pan-användning växer eller vid nästa större annoteringsfunktion (multi-klass-etiketter i rutor, splines/klassfärgade fyllningar, etc.)**

Motivering:

- Dagens canvas är nyligen utbyggd (markörer, Delete/Backspace, zoom/pan, dirty-spårning, negativa exempel) och hela beteendet är testat — att porta nu betalar inte omkostnaden (skattning: 1-2 dagar inklusive testomskrivning) mot vinsten (≈250 rader mindre kod).
- Prototypen visar att porten är lågtrösklig och välgörande när den väl görs: kosmetiska pennor och gratis zoom tar bort de bitar av vår egna matte som är svårast att underhålla. Att QGraphicsScene är rätt slutmål är därför inte helst ett frågetecken längre.
- Triggerpunkter för porten: (a) zoom under 0,5x eller närhetskrav i verklig användning visar koordinatbrister, (b) annoteringen utökas med funktioner som scenen ger gratis (svg-liknande, textobjekt, skikt), (c) buggar i Canvas-hanteringen dyker upp igen vid mus-tangentinteraktioner.

**Nästa steg (senare, separat task):** port av AnnotationCanvas till AnnotationView enligt prototypen, med bibehållen signal-/dirty-semantik och testsviten omskriven i samma veva.

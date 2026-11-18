---
id: TASK-157
title: Träningsvy - tabell tidigare träningar
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-18T12:04:00Z'
updated_date: '2026-11-18T13:56:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 153000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
* Byt namn på kolumn "Körning" till "Datum" och formattera innehållet som vanligt datum och tid.
* Byt namn på kolumn "Basmodell" till "Checkpoint".
* Lägg in kolumn "Modellnamn" som andra kolumn mellan "Datum" och "Checkpoint".
* Byt namn på kolumnerna "Dom" och "Status" till "Status" och "Notering". Välj vilken av de nuvarande kolumnerna som passar bäst till respektive ny rubrik (tycker innehållet är ganska likt).
* Uppdatera även statusraden under tabellen och eventuella referenser i kod/dokumentation med de nya begreppen.
<!-- SECTION:DESCRIPTION:END -->

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
1. Lägg till started_text (lokalt 'YYYY-MM-DD HH:MM') och model_name (namn, annars '-') på TrainingRun.
2. Byt kolumnlistan i ui/training_history.py till Datum, Modellnamn, Checkpoint, Epoker, Tid, mAP50-95, Status, Notering; Status = status_label, Notering = verdict.label.
3. Byt 'Basmodell:' mot 'Checkpoint:' och 'Dom:' mot 'Notering:' i radan under tabellen.
4. Uppdatera testerna (kolumnindex, kolumnnamn) och docs/beteende.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Kolumner: Datum, Modellnamn, Checkpoint, Epoker, Tid, mAP50-95, Status, Notering. Datum är starttiden omräknad till lokal tid (TrainingRun.started_text), Modellnamn är manifestets name med '-' för äldre manifest (TrainingRun.model_name), Checkpoint är vikfilens namn. Status visar status_label och Notering visar verdict.label. Radan under tabellen och docs/beteende.md använder checkpoint/notering.

Verifiering: 901 passed, 1 skipped (pytest -n 4). ruff check utan anmärkning. Vyn renderad offscreen med två körningar: kolumnerna och raden under tabellen visar de nya begreppen.

Uppföljning efter testkörning: första kolumnen tog allt överskott eftersom den låg i Stretch. Nu får varje kolumn sin innehållsbredd plus en jämn del av det som blir över (_distribute_columns), och fördelningen räknas om när tabellens synliga yta byter bredd via ett eventfilter på viewporten. Ryms inte innehållet behåller kolumnerna sin bredd och tabellen rullar i sidled. Commit fd21d8f.

Uppföljning 2: kryssrutans kolumn tar ingen del av överskottsbredden utan håller sig till kryssrutans bredd (40 px), medan de åtta datakolumnerna delar resten. Ett klick var som helst i kryssrutecellen slår nu om kryssrutan och väljer raden; Qt får inte sköta rutan själv (ItemIsUserCheckable borttagen), eftersom ett klick på indikatorn då hade slagit om två gånger. Verifierat med QTest.mouseClick på cellens högra del: krysset slås om, raden blir vald och Markera alla följer med. Hela sviten seriellt: 954 passed, 1 skipped. Commit f1d3d31.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Historiktabellen i träningsvyn visar nu Datum, Modellnamn, Checkpoint, Epoker, Tid, mAP50-95, Status och Notering. Datum är körningens starttid omräknad till lokal tid i stället för körnings-id:t, Modellnamn är namnet träningen gav modellen (manifest som skrevs innan namnet fanns visar '-'), och Checkpoint är viktfilen träningen utgick från. Status visar hur körningen slutade och Notering visar domen över epokkurvan, så de två liknande kolumnerna har fått var sin tydlig rubrik. Radan under tabellen och docs/beteende.md använder samma begrepp.

Verifierat med 901 passerade tester (1 skippat), ruff check utan anmärkning, och en offscreen-renderad vy med två körningar som visar de nya kolumnerna och den nya raden under tabellen. En testkörning föll på tests/test_shortcuts.py::test_delete_key_removes_the_selected_pairs, som är känd som instabil (TASK-34); den passerar både enskilt och vid omkörning av hela sviten.
<!-- SECTION:FINAL_SUMMARY:END -->

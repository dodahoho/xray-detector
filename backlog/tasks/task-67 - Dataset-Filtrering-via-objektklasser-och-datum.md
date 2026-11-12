---
id: TASK-67
title: Dataset - Filtrering via objektklasser och datum
status: Done
assignee:
  - '@vibe-mistral'
created_date: '2026-11-12T14:31:00Z'
updated_date: '2026-11-12T14:47:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Inför möjlighet att filtrera på objektklasser. Default visas alla men det ska vara möjligt att tex bara visa "pistol"

Det ska även vara möjligt att bara visa data som fångats inom ett datumintervall (via datepickers)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Alla fångster visas som default
- [x] #2 Klassfiltret visar bara fångster som innehåller vald klass
- [x] #3 Datumintervallet visar bara fångster som fångats inom intervallet
- [x] #4 Filtren kan kombineras och nollställas
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
1. Lägg en filterrad överst i datasetvyn: klassval (Alla klasser som default), kryssruta för datumintervall samt två datepickers.
2. Fyll klasslistan och datumgränserna från datasetet vid varje bygge, och behåll användarens val.
3. Filtrera fångsterna i _build: en fångst visas om den innehåller vald klass och ligger inom datumintervallet; osparade fångster filtreras på sina detektioner och sin tidsstämpel.
4. Bygg om listan från redan inläst data när filtret ändras, utan ny filläsning, och visa ett meddelande när inget matchar.
5. Test: default visar allt, klassfiltret, datumintervallet, kombinationen och nollställning.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Filterraden ligger under knappraden: klassval (QComboBox med "Alla klasser" som default), kryssruta för datumintervall och två QDateEdit med kalenderpopup. Klasslistan fylls från datasetets kategorier plus klasser som bara finns i osparade fångsters detektioner, och datumgränserna sätts första gången det finns datum. _build filtrerar fångsterna innan sektionerna skapas, så tomma datumsektioner inte blir kvar, och osparade fångster filtreras på sina detektioner och sin tidsstämpel. Ett filterbyte bygger om listan från redan inläst data i stället för att läsa om datasetet, och när inget matchar visas "Inga bilder matchar filtret.".
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Datasetvyn kan filtreras på objektklass och på datumintervall.

Vad som ändrades i xray_detector/ui/dataset_view.py:
- Filterrad överst i vyn: klassval med "Alla klasser" som default, kryssruta för datumintervall och två datepickers (från/till).
- _sync_filters fyller klasslistan från datasetets kategorier plus klasser som bara finns i osparade fångster, och sätter datumgränserna till datasetets äldsta och nyaste datum första gången; användarens val behålls vid ombyggnad.
- _build filtrerar fångsterna innan sektionerna skapas, så datumsektioner utan träffar försvinner; osparade fångster filtreras på sina detektioner och sin tidsstämpel.
- Ett filterbyte bygger om listan från redan inläst data i stället för att läsa om datasetet, och när inget matchar visas "Inga bilder matchar filtret.".

Verifiering:
- Nya tester i tests/test_dataset_filter.py: default visar allt, klassfiltret visar bara fångster med vald klass, filtret kan nollställas, datumintervallet begränsar listan, avstängt datumfilter visar allt igen, filtren kombineras, tomt resultat ger meddelandet, osparade fångster filtreras på klass, en klass som bara finns i en osparad fångst går att välja, och ombyggnaden läser inte om datasetet (load_coco får inte anropas).
- Hela sviten: 452 passed, 1 skipped.
- Renderad vy: klassvalet "pistol" lämnar bara pistol-fångsterna kvar, och datumintervallet 2026-11-10 lämnar bara den dagens fångster.
- ruff check på ändrade filer: inga anmärkningar.

Risker: filtret gäller bara det som redan är inläst, så en osparad fångst som skrivs till disk av en annan process syns först vid nästa omladdning. Datumgränserna sätts en gång per vy; växer datasetet med ett nyare datum får användaren flytta "till" själv.
<!-- SECTION:FINAL_SUMMARY:END -->

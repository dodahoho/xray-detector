---
id: TASK-68
title: Dataset - Titelrad card, bort med Markerad
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T16:40:00Z'
updated_date: '2026-11-12T17:19:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 66000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
I vy dataset behövs inte texten "Markerad" i titelraden för ett card eftersom man tydligt ser med ändrad bakgrundsfärg att kortet blir markerat. Badges för detekterade klasser kan då visas direkt efter tidsangivelsen i titelraden
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Titelraden i datasetvyn visar ingen text om markering
- [x] #2 Markeringen syns som ändrad bakgrundsfärg och ram på kortet
- [x] #3 Klassmärkena visas direkt efter tidsangivelsen i titelraden
- [x] #4 Kortet behåller sin storlek när fångsten markeras
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
1. Ta bort konstanten MARKED_SUFFIX och texten ' · Markerad' ur rubrikraden i xray_detector/ui/dataset_view.py.
2. Förenkla _capture_header: etiketten behöver inte längre mäta upp plats för suffixet (TASK-63-hacket), eftersom texten är konstant. Klassmärkena hamnar då direkt efter tidsangivelsen.
3. _update_group_header växlar bara färger; base_text i _group_headers blir död och tas bort (2-tupel).
4. Uppdatera testerna i test_dataset_selection.py, test_dataset_header.py, test_dataset_layout.py och test_pending.py.
5. Uppdatera README:s beskrivning av datasetvyn.
6. Kör testsviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rubrikraden i datasetvyn har ingen ' · Markerad'-text längre. Markeringen syns bara som färg: raden fylls med accentfärgen (#4da3ff) och kortet får samma ram, medan texten står still i alla lägen.

Ändringar i xray_detector/ui/dataset_view.py:
- MARKED_SUFFIX borttagen.
- _capture_header skapar etiketten med sin text direkt. Mätningen av bredd för suffixet (ensurePolished + setMinimumWidth) behövs inte när texten är konstant och är borttagen, så klassmärkena hamnar direkt efter tidsangivelsen.
- _update_group_header växlar bara färger. base_text i _group_headers var bara till för suffixet och är borta; posten är nu ett 2-tupel (etikett, kort).

Tester:
- test_dataset_selection.py::test_header_is_filled_and_marked kontrollerar att texten är oförändrad före, under och efter markering och att bara färgerna växlar.
- Ny test_dataset_header.py::test_badges_follow_directly_after_the_time: etiketten har sin naturliga bredd och första badgen ligger exakt ett layoutavstånd efter den. Testet faller om breddreservationen kommer tillbaka (verifierat: en etikett med minimumWidth bredare än sizeHint ger width != sizeHint).
- test_dataset_header.py, test_dataset_layout.py och test_pending.py uppdaterade för 2-tupeln.

Verifiering:
- Hela sviten: 453 passed, 1 skipped.
- ruff check på ändrade filer: inga anmärkningar.
- Renderad rubrikrad före/under/efter markering: radens bakgrund #f3f3f3 -> #4da3ff -> #f3f3f3, texten '09:56:38' hela tiden, kortet 500x226 i alla tre lägena.

Uppföljning efter avslutet: rubrikraden fick lite mer luft mellan tidsangivelsen och klassmärkena. TIME_BADGE_GAP (6 px) läggs till som ett mellanrum efter tidsetiketten, så avståndet tid->märke blir 10 px medan märkena sitter kvar 4 px isär. Gäller både sparade och osparade kort eftersom de delar _capture_header.

Verifiering: test_dataset_header.py::test_badges_follow_the_time_with_extra_air mäter avstånden i en utlagd rad (tid->märke 10 px, märke->märke 4 px) och kräver att det första är större än det andra. Hela sviten: 453 passed, 1 skipped. ruff check: inga anmärkningar.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Titelraden i datasetvyn visar inte längre någon text om markering; markeringen syns bara som färg och klassmärkena ligger direkt efter tidsangivelsen.

Vad som ändrades i xray_detector/ui/dataset_view.py:
- MARKED_SUFFIX (' · Markerad') är borttagen.
- _capture_header skapar tidsetiketten med sin text direkt. Mätningen som reserverade plats för suffixet (ensurePolished + setMinimumWidth) är borttagen, eftersom texten är konstant; därför hamnar klassmärkena direkt efter tiden.
- _update_group_header växlar bara färger. Den sparade bastexten i _group_headers behövdes bara för suffixet och är borta, så posten är nu (etikett, kort).

Verifiering:
- tests/test_dataset_selection.py::test_header_is_filled_and_marked: texten är oförändrad före, under och efter markering; bara radens och kortets färger växlar.
- Ny tests/test_dataset_header.py::test_badges_follow_directly_after_the_time: etiketten har sin naturliga bredd och första badgen ligger exakt ett layoutavstånd efter den. Testet faller om breddreservationen återinförs.
- TASK-63-testerna för oförändrad kortstorlek (test_dataset_layout.py, test_dataset_card_click.py) passerar oförändrade.
- Hela sviten: 453 passed, 1 skipped. ruff check: inga anmärkningar.
- Renderad rubrikrad före/under/efter markering: bakgrund #f3f3f3 -> #4da3ff -> #f3f3f3, texten '09:56:38' hela tiden, kortet 500x226 i alla tre lägena.

Risker: ingen känd. _group_headers är intern och bara testad i projektet; alla anrop är uppdaterade.
<!-- SECTION:FINAL_SUMMARY:END -->

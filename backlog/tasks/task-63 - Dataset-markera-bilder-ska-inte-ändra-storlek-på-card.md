---
id: TASK-63
title: Dataset - markera bilder ska inte ändra storlek på card
status: Done
assignee:
  - '@vibe-mistral'
created_date: '2026-11-12T12:57:00Z'
updated_date: '2026-11-12T14:09:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/dataset_view.py
  - tests/test_dataset_layout.py
  - README.md
type: enhancement
ordinal: 61000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu när man markerar bildpar i vyn dataset så ändras storleken på car lite. Det gör att positioner flyttas och vyn blir hoppig. Önskvärt är att card för bilpar behåller samma yttre storlek så att positionerna på objekt i vyn hålls fasta.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Kortet för ett bildpar har samma yttre storlek före och efter markering
- [x] #2 Korten intill behåller sina positioner när ett bildpar markeras
- [x] #3 Rubriken avslutas fortfarande med Markerad vid markering
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
1. Gör rambredden på Thumbnail konstant (3 px) och växla bara färg vid markering.
2. Gör kortets rambredd konstant (1 px) och växla bara färg; samma för osparade kort.
3. Ge rubrikraden fasta contentsMargins i båda lägena i stället för padding enbart i det markerade läget.
4. Reservera bredden för ' · Markerad' när rubriken skapas, så textbytet inte ändrar rubrikens storlek.
5. Test: kortets geometri och sizeHint är oförändrade efter markering, för både sparade och osparade fångster.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Kortet bytte storlek på tre ställen: Thumbnail-ramen gick från 3 till 4 px, kortets ram från 1 till 2 px och rubriken fick padding 2px 6px bara i markerat läge. Dessutom blev rubriken bredare av texten ' · Markerad'. Nu växlar bara färgerna på bild- och kortramen, rubriken har samma contentsMargins i båda lägena, och _capture_header reserverar bredden för det markerade läget när rubriken skapas. Rubriken mäts med kortet som förälder: utan förälder har stilmallen inte lagt på sin ram när bredden mäts, och då blev reservationen 9 px för liten. Mätt före/efter: kortet låg på 504x246 och blev 506x254 vid markering; nu är geometri och sizeHint oförändrade för både sparade och osparade fångster, även för enbildskort där rubriken är den bredaste delen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Kortet för ett bildpar behåller sin storlek när fångsten markeras, så korten intill inte flyttas.

Vad som ändrades i xray_detector/ui/dataset_view.py:
- Thumbnail-ramen har samma bredd (3 px) i båda lägena; bara färgen växlar.
- Kortets ram har samma bredd (1 px) i båda lägena; bara färgen växlar. Stilarna byggs nu av _header_style och _card_style så att bara färgerna skiljer.
- Rubriken har samma contentsMargins i båda lägena i stället för padding enbart i det markerade läget.
- _capture_header reserverar bredden för ' · Markerad' redan när rubriken skapas, så textbytet inte ändrar rubrikens storlek. Rubriken mäts med kortet som förälder, annars har stilmallen inte lagt på sin ram och reservationen blir för liten.

Verifiering:
- Nya tester i tests/test_dataset_layout.py: test_selection_keeps_the_card_size_and_position och test_selection_keeps_the_pending_card_size jämför kortens geometri och sizeHint före och efter markering. Båda fallerar mot koden före ändringen (kortet gick 504x246 -> 506x254 och korten intill flyttades) och passerar nu.
- Hela sviten: 429 passed, 1 skipped.
- Renderad vy före/efter markering: rubriken fylls med accentfärg och avslutas med 'Markerad', bilderna får blå ram, och korten intill står kvar på samma position.
- ruff check: inga anmärkningar.

Risker: rubrikens reserverade bredd mäts en gång när vyn byggs. Byts appens typsnitt vid körning utan att listan byggs om kan reservationen bli för liten, men teman i appen byter bara paletten, inte typsnittet.
<!-- SECTION:FINAL_SUMMARY:END -->

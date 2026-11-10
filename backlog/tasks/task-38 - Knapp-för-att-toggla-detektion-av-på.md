---
id: TASK-38
title: Knapp för att toggla detektion av/på
status: Done
assignee: []
created_date: '2026-11-10T20:11:00Z'
updated_date: '2026-11-10T22:34:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/detection_view.py
  - tests/test_detection_toggle.py
  - README.md
  - xray_detector/infrastructure/video/camera_service.py
  - tests/test_stream_worker.py
type: feature
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Kan finnas tillfällen där man vill slå av objektdetektion. Lägg in knapp längst till höger i rubrikraden ovanför videofönstrena
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Detektionsvyn har en knapp längst till höger i rubrikraden ovanför videofönstren
- [x] #2 Knappen slår av och på objektdetektionen i båda strömmarna
- [x] #3 När detektionen slås på igen används samma modell utan omladdning
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
1. Lägg en checkbar knapp sist i rubrikraden i DetectionView (efter "Fånga bilder"), med text som visar läget: "Detektion på" / "Detektion av".
2. Håll läget i DetectionView.detection_enabled. Av: koppla bort detektorn från video_service (set_detector(None)) och rensa overlayn. På: koppla tillbaka samma detektor-instans, utan att ladda om modellen.
3. Låt läget styra alla vägar som kopplar in detektorn: ny/återställd videokälla, modellbyte och resume_detection efter träningspaus (pause_detection frigör fortfarande VRAM).
4. Nya tester i tests/test_detection_toggle.py: knappens placering, av/på utan omladdning, overlay rensas, ny källa får ingen detektor i av-läget, resume efter träning respekterar av-läget.
5. Uppdatera README (detektionsläget) och kör hela testsviten plus ruff.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Knappen är en checkbar QPushButton sist i rubrikraden (efter "Fånga bilder") med texten "Detektion på" / "Detektion av". Läget hålls i DetectionView.detection_enabled och styr alla vägar som kopplar in detektorn: _active_detector() används vid ny videokälla och vid modelladdning, och resume_detection() lämnar detektionen avstängd efter en träningspaus om användaren slagit av den. Modellen ligger kvar i minnet vid avslag, så påslaget går snabbt; läget sparas inte mellan starter.

Bug hittad vid verifiering: StreamWorker emitterade föregående frames detektioner även efter att detektorn kopplats bort, eftersom listan var en lokal variabel i run(). Överlayn låg därför kvar med frysta rutor. Detektionerna är nu ett instansfält som nollställs i set_detector(), och ett resultat som blir klart efter bortkopplingen kastas (identitetskontroll på detektorn). Samma fel gjorde att pause_detection() vid träning lämnade kvar rutor i strömmen.

Verifiering: 9 nya tester (8 i tests/test_detection_toggle.py, 1 i tests/test_stream_worker.py). Hela sviten 164 passed, 1 skipped, tre körningar i rad utan flakighet. Regressionstestet fäller utan worker-fixen (kontrollerat genom att tillfälligt återställa camera_service.py). End-to-end mot media/xray_slideshow_side.mp4: 42 av 44 ramar med rutor när detektionen är på, 0 av 45 när den är av, 44 av 46 när den slås på igen. Ruff: inga nya anmärkningar (de fem som finns i berörda filer fanns före ändringen).

Rättelse efter granskning: knapptexten beskriver nu vad ett klick gör i stället för nuvarande läge. Vid start står "Detektion av" (detektionen är igång) och efter klick står "Detektion på". Konstanterna heter DETECTION_TURN_OFF / DETECTION_TURN_ON för att inte förväxlas med läget. Verifierat med klicksekvens: start 'Detektion av' checked=True, klick 1 'Detektion på' checked=False, klick 2 'Detektion av' checked=True. Hela sviten 164 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Detektionsvyn har fått en checkbar knapp längst till höger i rubrikraden. Knapptexten säger vad ett klick gör: "Detektion av" när detektionen är igång (även vid start) och "Detektion på" när den är av. Avslaget kopplar bort detektorn från båda strömmarna och rensar overlayn, men modellen ligger kvar i minnet, så påslaget sker utan omladdning. Läget styr också nya videokällor, modellbyten och återupptagningen efter en träningspaus, och sparas inte mellan starter.

Verifieringen avslöjade ett fel i StreamWorker: efter att detektorn kopplats bort fortsatte den att emittera föregående frames detektioner, eftersom listan var lokal i run(). Överlayn låg därför kvar med frysta rutor, vilket också drabbade den befintliga pausen vid träning. Detektionerna är nu ett instansfält som nollställs i set_detector(), och ett detektionsresultat som blir klart efter bortkopplingen kastas.

Nio nya tester; hela sviten 164 passed, 1 skipped, stabilt över tre körningar. End-to-end mot en demovideo: 42 av 44 ramar med rutor påslaget, 0 av 45 avslaget, 44 av 46 när det slogs på igen. Klicksekvensen ger 'Detektion av' -> 'Detektion på' -> 'Detektion av'. README beskriver knappen.
<!-- SECTION:FINAL_SUMMARY:END -->

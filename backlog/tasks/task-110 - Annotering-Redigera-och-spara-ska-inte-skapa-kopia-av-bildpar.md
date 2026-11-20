---
id: TASK-110
title: Annotering - Redigera och spara ska inte skapa kopia av bildpar
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T08:23:00Z'
updated_date: '2026-11-17T09:07:00Z'
labels: []
dependencies: []
type: bug
ordinal: 358000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Om man öppnar ett befintligt bildpar så att man hamnar i annoteringsläge, gör en ändring och trycker spara så skapas det nu ett nytt bildpar och det gamla finns kvar. Det ska inte bli en kopia i det här läget. Ändring som sparas ska ersätta det befintliga bildparet.
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
1. StreamFrame får dataset_id, som datasetvyn sätter när den öppnar ett sparat bildpar.
2. AnnotationView.load_captures sparar id-listan och _write använder replace_samples när listan är satt, annars add_samples som förut.
3. DatasetStore.replace_samples skriver om bild och labels på plats och behåller id, grupp, fångsttid och synthetic/source, så paret ligger kvar i datasetet. Antalet bilder som inte stämmer faller tillbaka på delete + add.
4. Tester: spara ett sparat par ger fortfarande ett par med samma id, och en ny fångst lägger fortfarande till ett par.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
StreamFrame har fått dataset_id, som datasetvyn sätter när den öppnar ett sparat bildpar. AnnotationView.load_captures samlar id-listan i self.dataset_ids, och _write går till replace_samples när listan är satt och annars till add_samples som förut. En ny fångst från detektionsvyn har inga dataset_id och lägger därför fortfarande till ett par.

DatasetStore.replace_samples skriver om bilden och labels på plats och behåller id, group, captured och synthetic/source, så ett redigerat par ligger kvar på samma plats och en redigerad variation fortsätter höra till sitt ursprung. num_objects räknas om med de gamla annoteringarna borträknade. Stämmer antalet bilder inte med antalet id:n raderas de gamla och bilderna läggs till som nya.

tests/test_gui_smoke.py::test_gui_capture_annotate_save_roundtrip förväntade den gamla kopieringen (2 bilder, 2 grupper efter en sparning); den är uppdaterad till 1 bild och 1 grupp.

Verifierat: 3 nya tester i tests/test_annotation_save_button.py och 3 i tests/test_dataset_store.py. Hela sviten: 812 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
En redigering av ett sparat bildpar ersätter paret i stället för att lägga till en kopia. Datasetvyn sätter dataset_id på ramarna den öppnar, och sparningen går då till DatasetStore.replace_samples, som skriver om bild och labels på plats och behåller bild-id, fångstgrupp, fångsttid och synthetic/source. Paret ligger därför kvar på samma plats i datasetet, och en redigerad variation fortsätter höra till sitt ursprung. En ny fångst från detektionsvyn lägger fortfarande till ett nytt par.

Antalet bilder som inte stämmer med antalet id:n faller tillbaka på delete + add, så en halvladdad bild inte lämnar datasetet i ett mellanläge.

Verifierat med 6 nya tester: att en redigerad bild behåller id och grupp, att synthetic/source bevaras, fallback vid antalsmismatch, samt tre tester genom MainWindow som visar att ett sparat par stannar på en bild och att en ny fångst fortfarande läggs till. tests/test_gui_smoke.py::test_gui_capture_annotate_save_roundtrip förväntade den gamla kopieringen och är uppdaterad. Hela sviten: 812 passed, 1 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->

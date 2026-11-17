---
id: TASK-108
title: Namngivning av tränad modell
status: Done
assignee: []
created_date: '2026-11-17T08:15:00Z'
updated_date: '2026-11-17T09:52:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 106000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Namnge tränad modell enligt mönster:

[Basmodell namn] [datum] [antal ursprungsbildpar + antal syntetiska bilder] [antal klasser]

T ex
YOLO26 large 2026-11-15 13+29 bildpar 4 klasser

Om en tränad modell vidaretränas med samma dataset är det endast datum som uppdateras
YOLO26 large 2026-11-17 13+29 bildpar 4 klasser

Basmodellens namn är alltid den modell man utgick från vid första träningen
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Namnet byggs i träningsvyn av basmodellens etikett, körningens datum, dataset_counts() (ursprungsbildpar + syntetiska bilder) och antalet klasser i datasetet. Det skickas som --name till träningsprocessen, som sparar det i manifestet tillsammans med base_model_name.

base_model_name ärvs: ModelSpec har fått base_name, som trained_models() fyller från manifestet. Träningsvyn använder spec.base_name eller spec.label, så en vidareträning på en egen tränad modell behåller ursprungsnamnet och bara datumet byts. ModelCatalog.save() skriver bara key/label/family/weights, så base_name hamnar inte i models.json.

trained_models() använder manifestets name som etikett; manifest utan name (skrivna före TASK-108, eller körda från CLI:t utan --name) behåller Tränad <körning> (<basmodell>).

Verifierat: 8 nya tester över domänfunktionen, manifestet, worker-kommandot, modellväljaren, models.json och träningsvyn. Hela sviten: 812 passed, 1 skipped.

Förtydligat efter fråga: talet efter plustecknet räknar syntetiska bildpar, inte syntetiska bilder. Varje variation blir en egen fångstgrupp, så dataset_counts() räknar grupper bland de syntetiska bilderna. 3 ursprungspar med två variationer var ger alltså 3+6 bildpar, inte 3+12.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
En tränad modell namnges nu enligt [basmodell] [datum] [ursprungsbildpar + syntetiska bildpar] bildpar [antal klasser] klasser, till exempel YOLO26 large 2026-11-15 13+29 bildpar 4 klasser. Båda talen räknar bildpar: en variation blir ett eget bildpar, så en utökning med två variationer per ursprungspar höjer talet efter plustecknet med två per par. Träningsvyn bygger namnet och skickar det till träningsprocessen, som sparar name och base_model_name i manifestet; modellväljaren använder name som etikett.

Basmodellens namn ärvs genom ModelSpec.base_name, som fylls från manifestet, så en vidareträning på en egen tränad modell behåller ursprungsnamnet och bara datumet uppdateras. Manifest som skrevs före ändringen, och körningar från CLI:t utan --name, behåller etiketten Tränad <körning> (<basmodell>).

Verifierat med 8 nya tester: mönstret, singular för en klass, manifestets name/base_model_name, tomt namn från CLI:t, worker-kommandot, modellväljarens etikett och ärvda basnamn, att base_name inte hamnar i models.json, samt träningsvyns namnberäkning. En riktig körning på 3 ursprungspar med två variationer var ger 3+6 bildpar. Hela sviten: 812 passed, 1 skipped.
<!-- SECTION:FINAL_SUMMARY:END -->

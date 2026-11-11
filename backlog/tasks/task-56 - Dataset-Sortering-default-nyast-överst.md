---
id: TASK-56
title: Dataset - Sortering default nyast överst
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T21:11:00Z'
updated_date: '2026-11-11T21:16:00Z'
labels: []
dependencies: []
ordinal: 54000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
De fångade bilderna är sorterade så att senaste datum hamnar längst ner i listan. Ordningen ska vara tvärtom så att de nyaste hamnar överst.
Det kan även läggas in en inställning för att ändra sortering "Nyast först" eller "Äldst först"
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Fångstgrupperna listas med den nyaste fångsten överst som standard
- [x] #2 Datasetvyns inställningar har valet "Nyast först"/"Äldst först" som sparas och styr ordningen
- [x] #3 Osparade fångster följer samma ordning som de sparade
- [x] #4 README och groma-arkitekturen beskriver sorteringen
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
1. dataset_view.py: fångstgrupperna sorteras fallande på grupp-id (nyaste först) som default; osparade fångster följer samma ordning.
2. settings_dialog.py: ny DatasetSortSection med valet 'Nyast först'/'Äldst först' som sparar direkt i QSettings (dataset/sort_order).
3. dataset_view.py: vyns inställningsknapp öppnar DatasetSortSection, så knappen blir aktiv.
4. Tester: ny testfil för sorteringen (default nyast först, äldst först via inställningen, osparade fångster) samt uppdaterad test_settings_dialog.py.
5. README och groma-arkitekturen (dataset-view.md) beskriver sorteringen.
6. Verifiering: hela testsviten och ruff på ändrade filer.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Sorteringen sker på grupp-id, som DatasetStore.add_samples tilldelar löpande (max befintligt + 1), så ordningen följer fångstordningen. Osparade fångster har millisekundstidsstämplar som grupp-id och sorteras redan nyast först av list_pending; vyn vänder på listan när äldst först är valt. Inställningen ligger i QSettings under dataset/sort_order med 'newest' som default, och sort_order() i settings_dialog.py läser den med fallback så ett okänt värde inte kan ge en tom lista. Datasetvyns inställningsknapp var tidigare avstängd; den öppnar nu DatasetSortSection och bygger om listan när valet ändras.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Datasetvyn listar nu den nyaste fångsten överst. Ordningen styrs av inställningen dataset/sort_order, som sätts i vyns inställningar (Alt+I) med valet Nyast först/Äldst först; knappen var tidigare avstängd och öppnar nu en DatasetSortSection. När valet ändras byggs listan om direkt, och osparade fångster från pending-kön följer samma ordning. Sorteringen sker på grupp-id, som DatasetStore tilldelar löpande, så den följer fångstordningen utan att tolka tidsstämplar. Verifierat med hela testsviten (276 passed, 1 skipped) och ruff på de ändrade filerna; nya test_dataset_sort.py täcker default, äldst först, omslag vid ändrat val och osparade fångster. README och groma (dataset-view.md, settings-dialog.md) beskriver sorteringen. Kvar att göra: ingen känd följdändring.
<!-- SECTION:FINAL_SUMMARY:END -->

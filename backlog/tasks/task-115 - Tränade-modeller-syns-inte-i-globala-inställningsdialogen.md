---
id: TASK-115
title: Tränade modeller syns inte i globala inställningsdialogen
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T11:59:00Z'
updated_date: '2026-11-17T12:14:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/application/model_registry.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/model_settings.py
  - xray_detector/ui/settings_view.py
  - tests/test_model_settings.py
  - tests/test_model_layout.py
  - README.md
type: bug
ordinal: 185000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Där modeller kan läggas till, tas bort och byta namn syns nu bara basmodellerna, inte de som tränats i applikationen.

Det samma lista med tillgängliga modeller bör hanteras överallt i applikationen så det är konsekvent
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Modellistan i de globala inställningarna visar både basmodeller och egentränade modeller
- [x] #2 Detektionsvyn och inställningsdialogen bygger sina listor ur samma funktion
- [x] #3 En egentränad modell kan inte bytas namn på eller tas bort i dialogen, eftersom träningskörningens manifest äger den
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
1. Inför available_models(models_dir, trained_dir) i application/model_registry.py som enda källa till 'alla modeller appen kan använda' (base_models + trained_models).
2. Låt DetectionView.refresh_models använda available_models i stället för att själv sätta ihop listan.
3. Låt ModelSection ta emot trained_dir (default models_dir/trained, samma som AppConfig.trained_dir) och lista available_models. Egentränade modeller visas men är skrivskyddade: byt namn och ta bort avstängs och statusraden förklarar att träningskörningen äger dem.
4. Uppdatera SettingsView att skicka in config.trained_dir.
5. Tester: sektionen listar tränade modeller, knapparna är avstängda för dem, och väljarna i detektionsvyn följer samma lista. Uppdatera README:s beskrivning av models.json.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
available_models(models_dir, trained_dir) i model_registry.py är nu enda källan till listan: basmodeller från models.json plus egentränade från models/trained/. Detektionsvyns refresh_models och ModelSection använder den. is_trained()/TRAINED_KEY_PREFIX avgör om en post ägs av ett träningsmanifest; sådana poster visas men Byt namn och Ta bort är avstängda, och en förklarande rad visas under listan. ModelSection tar trained_dir som valfri parameter med models_dir/trained som standard, samma som AppConfig.trained_dir.

Verifiering: tests/test_model_settings.py — listan innehåller 'trained-v3', knapparna är avstängda för den, en basmodell blir redigerbar igen, borttagning av en basmodell lämnar kvar de tränade, och inställningslistan har exakt samma nycklar som detektionsvyns väljare i ett riktigt MainWindow. tests/test_model_layout.py — available_models kombinerar bas och tränade i rätt ordning. Hela sviten: 829 passed, 1 skipped.

Träningsvyns väljare är avsiktligt kvar på base_models(), eftersom fältet heter 'Basmodell' och en träning utgår från en basmodell.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Modellistan i de globala inställningarna visar nu både basmodeller och egentränade modeller. available_models() i model_registry.py är enda källan till listan, så inställningarna och detektionsvyns väljare inte längre kan visa olika modeller. Egentränade modeller är skrivskyddade i dialogen eftersom träningskörningens manifest äger dem: Byt namn och Ta bort är avstängda och en rad under listan förklarar varför. README beskriver den delade listan. Verifierat med fem nya tester i tests/test_model_settings.py, ett i tests/test_model_layout.py och hela sviten (829 passed, 1 skipped). Träningsvyns 'Basmodell' är medvetet oförändrad.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-119
title: Ta bort tidigare träning av modell
status: Done
assignee:
  - '@david'
created_date: '2026-11-17T13:56:00Z'
updated_date: '2026-11-17T14:29:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 181000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Det måste finnas ett sätt att ta bort specifik träning av modell. Den ska då tas bort från vyn träning, samt att dess tillhörande filer trainingsloggar modellvikter osv tas bort. En borttagen träning ska även göra att den inte längre finns i listan över valbara modeller i applikationen.

Om man via globala inställningsdialogen vill ta bort en egentränad modell ska man få en dialog som varnar att borttagning av en egentränad modell även kommer att radera träningsfiler. Om ok i dialog så tas den bort på samma sätt som om man från vyn för träning hade valt att ta bort den aktuella träningen av modellen.

Alltså samma genomförande oavsett om man tar bort tränad modell via globala inställningarna eller via vyn med tidigare träningar
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
1. delete_run(trained_dir, run_id) i application/training_history.py tar bort körningskatalogen med vikter, manifest, metrics och utvärdering; trained_run_id(spec) i model_registry.py ger körningen bakom en egentränad modells nyckel.
2. Träningsvyns historik får knappen Ta bort träning med bekräftelsedialog; en pågående körning kan inte tas bort.
3. Modellistan i de globala inställningarna får ta bort en egentränad modell efter en varning om att träningsfilerna raderas, via samma delete_run.
4. Signaler uppdaterar modellväljarna och modellistan när en körning tas bort i träningsvyn, och historiken när en modell tas bort i inställningarna.
5. Tester för borttagning i båda vyerna samt README.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat: delete_run(trained_dir, run_id) i application/training_history.py raderar körningskatalogen med vikter, manifest, metrics och evaluation.json, och vägrar sökvägar utanför models/trained/. trained_run_id(spec) i model_registry.py ger körningen bakom en egentränad modells nyckel.

Träningsvyns historik har knappen Ta bort träning (Alt+B) med bekräftelsedialog. En pågående körning kan inte tas bort, eftersom träningen skriver i katalogen. Modellistan i de globala inställningarna kan nu ta bort en egentränad modell efter en varning om att träningsfilerna raderas; båda vägarna anropar samma delete_run.

Signaler: TrainingView.models_changed uppdaterar detektionsvyns väljare och modellistan, och settings_view.models_changed uppdaterar även historiklistan, så en borttagning slår igenom i alla listor oavsett var den gjordes.

Den delade logs/training.log lämnas orörd eftersom den innehåller alla körningars utmatning; körningens egna filer ligger i körningskatalogen och raderas med den.

Verifiering: 859 passed, 1 skipped (hela sviten). Ruff utan anmärkning på ändrade filer; den befintliga I001 i model_registry.py:218 är orörd. Nya tester i tests/test_training_history.py och tests/test_model_settings.py.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Träningar kan nu tas bort med sina filer. Träningsvyns historik har knappen Ta bort träning (Alt+B) som efter en bekräftelse raderar körningskatalogen – vikter, manifest, metrics och evaluation.json – så modellen försvinner ur modellväljarna. Modellistan i de globala inställningarna kan ta bort en egentränad modell efter en varning om att träningsfilerna raderas; båda vägarna anropar samma delete_run, så genomförandet är identiskt. En pågående körning kan inte tas bort eftersom träningen skriver i katalogen.

Verifiering: hela testsviten 859 passed, 1 skipped. Nya tester täcker delete_run (inklusive skyddet mot en sökväg utanför models/trained/), bekräftelsedialogerna och att en borttagning i ena vyn uppdaterar den andra vyns lista. Ruff utan anmärkning på ändrade filer.

Risker: den delade logs/training.log lämnas orörd eftersom den innehåller alla körningars utmatning; bara körningens egna filer raderas. En modell som detektionsvyn redan har laddat ligger kvar i minnet tills en annan modell väljs, samma beteende som när en modell tas bort ur listan sedan tidigare.
<!-- SECTION:FINAL_SUMMARY:END -->

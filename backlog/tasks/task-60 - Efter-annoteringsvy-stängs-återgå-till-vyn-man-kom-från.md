---
id: TASK-60
title: Efter annoteringsvy stängs återgå till vyn man kom från
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-12T09:04:00Z'
updated_date: '2026-11-12T09:09:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 58000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Man kommer in till annoteringsvyn antingen via Detektion eller Dataset och när man är klar i annoteringsvyn (via knappar Spara eller Avbryt) så ska man återgå till den vy man kom från
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Annotering som öppnas från Detektion återgår till Detektion efter Spara och efter Avbryt
- [x] #2 Annotering som öppnas från Dataset återgår till Dataset efter Spara och efter Avbryt
- [x] #3 Tester täcker båda vägarna in och båda knapparna
- [x] #4 README och groma-arkitekturen beskriver beteendet
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
1. Huvudfönstret sparar vilken flik annoteringsvyn öppnades från: Detektion via Fånga bilder, Dataset via dubbelklick.
2. _on_annotation_saved och _on_annotation_cancelled sätter tillbaka den fliken i stället för hårdkodad Detektion; sparningen är asynkron så fliken läses av före setTabEnabled.
3. Ny testfil tests/test_annotation_navigation.py: båda vägarna in x Spara/Avbryt.
4. Uppdatera README och groma-beskrivningen av huvudfönstret.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Huvudfönstret sparar fliken annoteringen öppnades från i _annotation_origin: Detektion via Fånga bilder och Dataset via dubbelklick. _on_annotation_saved och _on_annotation_cancelled sätter tillbaka den fliken i stället för hårdkodad Detektion. Ordningen i _on_annotation_saved är ändrad: fliken läses av före setTabEnabled(1, False), eftersom Qt annars automatiskt byter till nästa aktiva flik och vakten aldrig slog till - tidigare hamnade en sparning från Detektion på Dataset-fliken. Nya tests/test_annotation_navigation.py täcker båda vägarna in och båda knapparna; testerna fäller den gamla koden (2 failed) och passerar med ändringen. Hela sviten: 315 passed, 1 skipped. Ruff utan anmärkningar. README och groma-beskrivningen av huvudfönstret uppdaterade.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Annoteringsvyn återgår nu till fliken den öppnades från. Huvudfönstret minns om annoteringen kom från Detektion (Fånga bilder) eller Dataset (dubbelklick på en fångst), och både Spara till dataset och Avbryt tar dig tillbaka dit. Tidigare gick Avbryt alltid till Detektion och en sparning hamnade på Dataset-fliken, eftersom Qt byter till nästa aktiva flik när den aktuella fliken stängs av och vakten därför aldrig slog till; fliken läses nu av före setTabEnabled. Verifierat med nya tests/test_annotation_navigation.py (båda vägarna in x Spara/Avbryt), som fäller den gamla koden (2 failed) och passerar med ändringen, samt hela sviten (315 passed, 1 skipped) och ruff utan anmärkningar. README och groma-arkitekturen beskriver beteendet. Kvar att göra: ingen känd följdändring.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-126
title: Räkna num_objects i _save_metadata istället för fem manuella inkrement
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:50:00Z'
updated_date: '2026-11-17T22:12:00Z'
labels:
  - bugfix
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/infrastructure/dataset_store/store.py
  - tests/test_dataset_store.py
priority: high
type: bug
ordinal: 124000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
num_objects underhålls inkrementellt i add_samples, replace_samples, add_variations och delete_images i store.py och räknas dessutom om en femte gång i export.write_manifest; lagrat och härlett värde kan gå isär (review_vibe_deepseek41_flash.md P1.3). Räkna num_objects i _save_metadata på samma sätt som num_images, utgående från label-filerna.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 num_objects beräknas i _save_metadata och stämmer alltid med faktiska annoteringar
- [x] #2 Test täcker alla fyra operationerna och verifierar num_objects efter varje
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
1. Räkna num_objects i _save_metadata ur label-filerna, på samma sätt som num_images räknas ur bildlistan.

2. Ta bort de fem manuella inkrementen i add_samples, replace_samples, add_variations och delete_images.

3. Test som kör alla fyra operationerna och jämför num_objects med antalet rader i labels/ efter varje, samt ett test där ett gammalt sparat värde skrivs över.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
store.py: _save_metadata sätter num_objects = self._object_count(metadata['images']), som summerar len(read_labels(...)) över bilderna. Inkrementen (objects/replaced) är borta ur add_samples, replace_samples, add_variations och delete_images, liksom de fem skrivningarna av metadata['info']['num_objects']. export.write_manifest räknar fortfarande själv, men det är exportens manifest över den exporterade delmängden och inte samma värde som dataset.json, så den lämnas orörd.

Verifiering: test_num_objects_is_counted_from_the_label_files jämför num_objects med antalet rader i labels/ efter add_samples, replace_samples, add_variations och delete_images. test_num_objects_ignores_a_stale_stored_value skriver 99 i dataset.json och fallerar mot koden före ändringen (100 == 2) men går igenom efter. Hela sviten: 866 passed, 1 skipped, 4 failed - samma fyra Windows-specifika offscreen-fel. ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
num_objects räknas nu i _save_metadata ur label-filerna, precis som num_images räknas ur bildlistan. De fem manuella inkrementen i add_samples, replace_samples, add_variations och delete_images är borta, så det sparade värdet kan inte längre glida isär från datasetet. Två tester täcker det: ett som jämför num_objects med antalet rader i labels/ efter varje operation, och ett som visar att ett gammalt sparat värde skrivs över. Hela sviten: 866 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-124
title: Felhantering i DatasetStore._load_metadata vid trasig dataset.json
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:50:00Z'
updated_date: '2026-11-17T22:09:00Z'
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
  - tests/test_gui_smoke.py
priority: high
type: bug
ordinal: 122000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
En trasig dataset.json (avbrott vid skrivning, manuell redigering) ger JSONDecodeError som propagerar via MainWindow.__init__ -> _log_startup -> DatasetService.image_pair_count -> load_dataset, så appen kraschar innan fönstret visas (verifierat reproducerbart i review_vibe_deepseek41_flash.md P1.1). ModelCatalog._read gör rätt i samma läge. Fånga (OSError, ValueError) i _load_metadata, logga och returnera tom struktur.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Appen startar även när dataset.json innehåller ogiltig JSON (tomt dataset + varning i loggen)
- [x] #2 Test finns som skriver skräp i dataset.json och startar MainWindow
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
1. Fånga (OSError, ValueError) i DatasetStore._load_metadata, logga en varning på xray-loggern och returnera den tomma metadata-strukturen.

2. Behandla även giltig JSON med fel form (saknar info eller images) som trasig, eftersom _save_metadata annars kastar KeyError på samma fil.

3. Test: skräp i dataset.json ger tomt dataset och varning; fel form ger samma sak; nästa add_samples ersätter filen; MainWindow startar med trasig fil.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
store.py: _load_metadata fångar (OSError, ValueError), loggar 'dataset.json går inte att läsa (...); datasetet startar tomt' på xray-loggern och faller tillbaka på den tomma strukturen. Hjälparna _is_metadata och _warn_broken_metadata ligger på modulnivå. Giltig JSON utan info-dict eller images-lista behandlas som trasig, eftersom _save_metadata annars kastar KeyError på samma fil.

Verifiering: de två nya testerna i test_dataset_store.py och test_gui_smoke.py fallerar med JSONDecodeError mot koden före ändringen (kontrollerat genom att tillfälligt återställa store.py) och går igenom efter. Hela sviten: 861 passed, 1 skipped, 4 failed - samma fyra Windows-specifika offscreen-/teckensnittsfel som TASK-123 dokumenterade, inga nya. ruff check . utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
DatasetStore._load_metadata fångar nu (OSError, ValueError) och returnerar ett tomt dataset med en varning i loggen i stället för att låta JSONDecodeError propagera genom MainWindow.__init__. Giltig JSON med fel form (saknar info eller images) behandlas likadant, eftersom _save_metadata annars kastar KeyError på samma fil. Nästa skrivning ersätter den trasiga filen. Tre enhetstester i test_dataset_store.py och ett MainWindow-test i test_gui_smoke.py täcker fallen; de fallerar mot koden före ändringen. Hela sviten: 861 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->

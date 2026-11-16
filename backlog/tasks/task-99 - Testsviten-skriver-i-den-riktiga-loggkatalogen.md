---
id: TASK-99
title: Testsviten skriver i den riktiga loggkatalogen
status: To Do
assignee: []
created_date: '2026-11-16T16:32:00Z'
labels: []
dependencies: []
priority: medium
type: bug
ordinal: 97000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-90. `tests/conftest.py:config` sätter `config.data_dir = tmp_path` men inte `logs_dir`, som därför står kvar på `PROJECT_ROOT / "logs"` enligt `domain/config.py:16`. Fixturens docstring påstår att loggkataloger ligger under `tmp_path` — det stämmer inte. Varje test som startar en träningsworker skriver därför i projektets riktiga `logs/training.log`. Verifierat: `pytest tests/test_training_chart.py tests/test_training_pause.py` (26 tester) ökade filen med 5 rader. Samtliga 246 rader i `logs/training.log` är pytest-körningar, så filen innehåller ingen riktig träning alls. Det gör loggen oanvändbar för felsökning och innebär att en testkörning skriver över historiken från verkliga körningar när rotationen slår till.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 En testkörning skriver inte i projektets logs-katalog
- [ ] #2 Testfixturens loggkatalog ligger under tmp_path som docstringen säger
- [ ] #3 Test täcker att en träningsworker i test skriver sin logg under tmp_path
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

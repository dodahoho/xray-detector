---
id: TASK-99
title: Testsviten skriver i den riktiga loggkatalogen
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:32:00Z'
updated_date: '2026-11-16T20:50:00Z'
labels: []
dependencies: []
priority: medium
type: bug
ordinal: 199000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-90. `tests/conftest.py:config` sätter `config.data_dir = tmp_path` men inte `logs_dir`, som därför står kvar på `PROJECT_ROOT / "logs"` enligt `domain/config.py:16`. Fixturens docstring påstår att loggkataloger ligger under `tmp_path` — det stämmer inte. Varje test som startar en träningsworker skriver därför i projektets riktiga `logs/training.log`. Verifierat: `pytest tests/test_training_chart.py tests/test_training_pause.py` (26 tester) ökade filen med 5 rader. Samtliga 246 rader i `logs/training.log` är pytest-körningar, så filen innehåller ingen riktig träning alls. Det gör loggen oanvändbar för felsökning och innebär att en testkörning skriver över historiken från verkliga körningar när rotationen slår till.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 En testkörning skriver inte i projektets logs-katalog
- [x] #2 Testfixturens loggkatalog ligger under tmp_path som docstringen säger
- [x] #3 Test täcker att en träningsworker i test skriver sin logg under tmp_path
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
1. Inför default_logs_dir() i domain/config.py som respekterar XRAY_LOGS_DIR, så sviten kan peka loggarna bort från projektets logs/ utan att varje test konstruerar om AppConfig.
2. Autouse session-fixture i tests/conftest.py som sätter XRAY_LOGS_DIR till en tmp-katalog, plus att config-fixturen sätter logs_dir = tmp_path / 'logs' som docstringen lovar.
3. Justera test_log_layout-testet som assertar projektets logs/ så det rensar XRAY_LOGS_DIR först.
4. Nytt test: en träningsworker i test skriver sin logg under tmp_path och inte i projektets logs/.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat: default_logs_dir() i domain/config.py läser XRAY_LOGS_DIR och faller annars tillbaka på projektets logs/. AppConfig.logs_dir använder den som default_factory. tests/conftest.py har en autouse session-fixture som sätter XRAY_LOGS_DIR till en tmp-katalog, så även tester som bygger AppConfig själva hamnar utanför den riktiga loggkatalogen, och config-fixturen sätter nu logs_dir = tmp_path / "logs" som docstringen lovar.

Verifierat: md5 för logs/app.log och logs/training.log är identiska före och efter en full svitkörning (765 passed, 1 skipped). Före ändringen växte logs/training.log från 71956 till 73263 byte av samma svit. Nya tester: test_logs_dir_env_override och test_training_worker_in_test_writes_under_tmp_path.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Testsviten skriver inte längre i projektets logs/. AppConfig.logs_dir hämtas via default_logs_dir(), som respekterar miljövariabeln XRAY_LOGS_DIR, och conftest sätter den till en tmp-katalog för hela sessionen. Det täcker även de tester som bygger AppConfig själva i stället för att använda config-fixturen, vilket var orsaken till att logs/training.log fylldes av pytest-körningar. config-fixturen sätter dessutom logs_dir = tmp_path / "logs", så fixturens docstring stämmer. Verifierat: md5 för båda loggfilerna är oförändrade efter en full svitkörning (765 passed, 1 skipped), mot att training.log växte 1307 byte före ändringen.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-98
title: Varningar från tredjepart når aldrig loggfilen
status: To Do
assignee: []
created_date: '2026-11-16T16:31:00Z'
labels: []
dependencies: []
priority: high
type: bug
ordinal: 96000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-90. Appen har tre loggsystem som skriver till olika destinationer. stdlib logging går till `logs/app.log`. rfdetr sätter `propagate = False` och egna stream-handlers i `rfdetr/utilities/logger.py`, så dess rader går bara till stderr. Python `warnings` (torch, transformers, rfdetr) går också bara till stderr, eftersom `logging.captureWarnings` aldrig anropas. Följden är att `logs/app.log` har 183 rader och noll av de varningar som syns i konsolen. Den som får loggfilen skickad sig kan inte se det som faktiskt stod i terminalen, och en verklig varning är omöjlig att skilja från brus. Dessutom är 76 av de 183 raderna `comtypes.client._code_cache` INFO — 41 % av filen är brus från en dependency, eftersom root-loggen saknar nivåstyrning per tredjepartslogger. Notera att TASK-36 medvetet lät DINOv2-varningarna om positional encodings och patch size stå kvar som signal; den här uppgiften handlar om att fånga dem, inte om att tysta dem.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Varningar som skrivs under en körning hamnar i logs/app.log med tidsstämpel
- [ ] #2 Kända ofarliga varningar från torch, transformers och rfdetr går att skilja från appens egna rader i filen
- [ ] #3 comtypes och motsvarande tredjepartsbrus hamnar inte i app.log
- [ ] #4 DINOv2-varningarna från TASK-36 finns fortfarande kvar som signal
- [ ] #5 Test täcker att en varning under körning hamnar i loggfilen
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

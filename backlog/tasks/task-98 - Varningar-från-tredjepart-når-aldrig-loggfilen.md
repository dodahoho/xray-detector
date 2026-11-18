---
id: TASK-98
title: Varningar från tredjepart når aldrig loggfilen
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T16:31:00Z'
updated_date: '2026-11-16T20:50:00Z'
labels: []
dependencies: []
priority: high
type: bug
ordinal: 202000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Upptäckt i TASK-90. Appen har tre loggsystem som skriver till olika destinationer. stdlib logging går till `logs/app.log`. rfdetr sätter `propagate = False` och egna stream-handlers i `rfdetr/utilities/logger.py`, så dess rader går bara till stderr. Python `warnings` (torch, transformers, rfdetr) går också bara till stderr, eftersom `logging.captureWarnings` aldrig anropas. Följden är att `logs/app.log` har 183 rader och noll av de varningar som syns i konsolen. Den som får loggfilen skickad sig kan inte se det som faktiskt stod i terminalen, och en verklig varning är omöjlig att skilja från brus. Dessutom är 76 av de 183 raderna `comtypes.client._code_cache` INFO — 41 % av filen är brus från en dependency, eftersom root-loggen saknar nivåstyrning per tredjepartslogger. Notera att TASK-36 medvetet lät DINOv2-varningarna om positional encodings och patch size stå kvar som signal; den här uppgiften handlar om att fånga dem, inte om att tysta dem.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Varningar som skrivs under en körning hamnar i logs/app.log med tidsstämpel
- [x] #2 Kända ofarliga varningar från torch, transformers och rfdetr går att skilja från appens egna rader i filen
- [x] #3 comtypes och motsvarande tredjepartsbrus hamnar inte i app.log
- [x] #4 DINOv2-varningarna från TASK-36 finns fortfarande kvar som signal
- [x] #5 Test täcker att en varning under körning hamnar i loggfilen
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
1. Lägg till capture_third_party_logs() i application/app_config.py: logging.captureWarnings(True), propagate=True för kända tredjepartsloggrar (rfdetr, rf-detr, ultralytics, torch, transformers, lightning, timm, supervision m.fl.) och WARNING-nivå på comtypes-bruset.
2. Anropa den från setup_logging() och igen efter import rfdetr i infrastructure/detectors/rfdetr_detector.py, eftersom rfdetr skapar sina loggrar först vid import.
3. Behåll %(name)s i LOG_FORMAT så tredjepartsrader (py.warnings, rf-detr, torch.*) går att skilja från appens xray-rader.
4. Tester: varning under körning hamnar i app.log, comtypes-INFO hamnar inte där, tredjepartsrad går att skilja från xray-rad, DINOv2-varningen finns kvar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat: capture_third_party_logs() i application/app_config.py. Den slår på logging.captureWarnings, sätter propagate=True på kända tredjepartsloggrar (rfdetr, rf-detr, ultralytics, torch, transformers, lightning, timm, supervision m.fl.) och håller comtypes på WARNING. Anropas från setup_logging() och igen efter import rfdetr i rfdetr_detector.py, eftersom rfdetr skapar sina loggrar först vid import. captureWarnings nollställs före den slås på: flaggan är global, och ett nytt anrop blir annars verkningslöst när något har återställt warnings.showwarning (som pytest:s catch_warnings gör mellan tester).

Verifierat: 6 nya tester i tests/test_third_party_logs.py. Hela sviten 765 passed, 1 skipped. Skarp körning av appen med XRAY_LOGS_DIR i en tmp-katalog gav 64 rader i app.log: DINOv2-varningarna från rf-detr, FutureWarning/TracerWarning från rfdetr under py.warnings, transformers.modeling_utils, och noll comtypes-rader (tidigare 76 av 183).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Apploggen fångar nu det som tidigare bara syntes i konsolen. capture_third_party_logs() slår på logging.captureWarnings så att Python-varningar från torch, transformers och rfdetr hamnar i app.log, och sätter propagate=True på tredjepartsloggrarna så att rfdetr:s egna rader når filen trots att paketet sätter propagate=False vid import. Fångsten görs om efter import rfdetr och efter modellbygget, eftersom loggrarna skapas först då. comtypes hålls på WARNING, vilket tog bort 41 % brus från filen. Loggerns namn i %(name)s skiljer tredjepartens rader (py.warnings, rf-detr, transformers.*) från appens xray-rader, och DINOv2-varningen från TASK-36 finns kvar som signal. Verifierat med 6 nya tester och en skarp appkörning: 64 rader, noll comtypes-rader, båda DINOv2-varningarna kvar.
<!-- SECTION:FINAL_SUMMARY:END -->

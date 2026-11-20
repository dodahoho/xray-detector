---
id: TASK-122
title: Konfigurera ruff i pyproject.toml och kör ruff check --fix
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:50:00Z'
updated_date: '2026-11-17T21:50:00Z'
labels:
  - ci
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - pyproject.toml
  - tests/prototype/test_prototype_annotation_scene.py
  - tests/test_annotation_ux.py
  - tests/test_app_config.py
  - tests/test_app_icon.py
  - tests/test_dataset_variations.py
  - tests/test_devices.py
  - tests/test_gui_smoke.py
  - tests/test_pending.py
  - tests/test_reconnect.py
  - tests/test_sample_video.py
  - tests/test_stream_worker.py
  - tests/test_training_scheduler.py
  - tests/test_training_worker.py
  - xray_detector/application/background_task.py
  - xray_detector/application/training_service.py
  - xray_detector/infrastructure/training/epoch_metrics.py
  - xray_detector/ui/detection_view.py
  - xray_detector/infrastructure/dataset_store/json_io.py
  - xray_detector/infrastructure/detectors/rfdetr_detector.py
  - xray_detector/ui/theme.py
  - xray_detector/infrastructure/dataset_store/store.py
  - xray_detector/infrastructure/detectors/smoothing.py
  - xray_detector/ui/annotation_view.py
  - tests/test_crash_dialog.py
  - tests/test_model_catalog.py
  - tests/test_model_classes.py
  - tests/test_third_party_logs.py
  - README.md
priority: high
type: chore
ordinal: 341000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Utvärderingarna (review_vibe_deepseek41_flash.md §5.1, utvärdering_argon.md §6.3) konstaterar att ruff finns som dev-beroende men saknar [tool.ruff]-sektion: 55 fel i defaultläge, 231 med utökade regler. Lägg till line-length=100, target-version=py311 och reglerna E,F,I,UP,B,SIM,C4,PERF,RUF; ignorera E501 och PLC0415 till en början så grinden kan slås på direkt. Kör sedan ruff check --fix (33+ fel försvinner automatiskt).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 [tool.ruff] och [tool.ruff.lint] finns i pyproject.toml med line-length 100 och target-version py311
- [x] #2 ruff check passerar utan fel efter ruff check --fix
- [x] #3 Hela pytest-sviten passerar fortfarande efter autofix
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
1. Lägg till [tool.ruff] (line-length=100, target-version="py311") och [tool.ruff.lint] (select E,F,I,UP,B,SIM,C4,PERF,RUF; ignore E501,PLC0415) i pyproject.toml. Verifierat mot ruff 0.17.3: den föreslagna uppsättningen ger 72 fel, varav 29 är autofixbara.
2. Lägg till allowed-confusables = ["–", "×", "−"] i [tool.ruff.lint] så att RUF001 inte flaggar avsiktlig svensk typografi (en dash i intervall/avskiljare, multiplikationstecken i upplösningar, minustecken på ikonknapp). RUF001 behålls aktiv för övriga tecken.
3. Kör ruff check --fix (F401, I001, SIM300, RUF100 försvinner automatiskt).
4. Åtgärda kvarvarande fel manuellt: SIM105 (contextlib.suppress), F841 (oanvända variabler), B905 (zip strict), SIM102 (ihoplagda if), RUF043 (escapade regex i pytest.raises), SIM108, PERF401, E402 (flytta class_color-import till toppnivå), RUF012 (ClassVar), B028 (stacklevel), RUF059 (_-prefix).
5. Verifiera: ruff check . ger 0 fel; riktade tester för ändrade moduler; därefter hela pytest-sviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Konfiguration: [tool.ruff] med line-length = 100 och target-version = "py311", [tool.ruff.lint] med select = E,F,I,UP,B,SIM,C4,PERF,RUF och ignore = E501,PLC0415 enligt taskbeskrivningen. Utöver beskrivningen lades allowed-confusables = ["–", "×", "−"] till: RUF001 gav annars 24 träffar som bara är svensk typografi i strängar (tankstreck, gånger-tecken, minustecken). Regeln är fortfarande aktiv för övriga konfunderbara tecken.

Autofix: ruff check --fix tog bort 30 fel (F401, I001, SIM300, RUF100). Kvarvarande 19 åtgärdades för hand: E402 (class_color-importen flyttad till toppnivå i detection_view.py), F841 x3, SIM102 x2, SIM105 x3 (contextlib.suppress), SIM108 x1, B905 x3 (strict=True i store.py och smoothing.py där längderna är garanterat lika; strict=False i annotation_view.py där antalet canvases kan överstiga antalet captures), B028, RUF012 (ClassVar), RUF059, RUF043 x2 (escapade punkter i match-mönster).

RUF100 tog bort två noqa: BLE001-direktiv (regeln är inte aktiverad). De förklarande kommentarerna behölls som vanliga kommentarer i background_task.py och epoch_metrics.py så avsikten finns kvar.

Dokumentation: README.md har ett kort avsnitt under Utveckla om ruff-grinden (uv run ruff check .).

Verifiering: ruff check . = All checks passed (0 fel), även via uv run ruff check . . Hela sviten: python -m pytest -q = 861 passed, 1 skipped in 243.35s. Den enda skippen är tests/test_rfdetr.py som hoppar över när rfdetr är installerat, alltså oförändrad av denna task.

Utanför scope, noterat: ruff format --check skulle formatera om 87 filer. Formatering ingår inte i tasken och är inte aktiverad som grind.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Lade till ruff-konfiguration i pyproject.toml: [tool.ruff] med line-length = 100 och target-version = "py311", [tool.ruff.lint] med select = E,F,I,UP,B,SIM,C4,PERF,RUF samt ignore = E501,PLC0415. Utöver taskbeskrivningen begränsades RUF001 med allowed-confusables = ["–", "×", "−"] eftersom de 24 träffarna bara var svensk typografi i strängar; regeln är kvar aktiv för övriga konfunderbara tecken.

ruff check --fix tog bort 30 fel automatiskt (F401, I001, SIM300, RUF100). De 19 kvarvarande åtgärdades för hand: E402 (class_color-importen till toppnivå), F841 x3, SIM102 x2, SIM105 x3 (contextlib.suppress), SIM108 x1, B905 x3 (strict=True där längderna är garanterat lika, strict=False i annotation_view.py där antalet canvases kan överstiga antalet captures), B028, RUF012 (ClassVar), RUF059 och RUF043 x2. Två noqa: BLE001 togs bort av RUF100; de förklarande kommentarerna behölls som vanliga kommentarer. README.md fick ett kort avsnitt under Utveckla om ruff-grinden.

Verifiering: ruff check . = All checks passed (0 fel), även via uv run ruff check . ; ruff check --show-settings bekräftar line_length = 100 och target 3.11 från repots pyproject.toml; python -m pytest -q = 861 passed, 1 skipped in 243.35s (skippen är rfdetr-testet som hoppar över när rfdetr är installerat). Committat som b06dddf.

Risker och uppföljningar: ruff format är inte aktiverad som grind (87 filer skulle formateras om) och ingår inte i tasken. B905 med strict=True i store.py och smoothing.py kan nu ge ValueError vid längdmissförhållande, vilket är avsiktligt och skyddat av befintliga längdkontroller. CI-jobbet i TASK-123 kan nu använda ruff check direkt.
<!-- SECTION:FINAL_SUMMARY:END -->

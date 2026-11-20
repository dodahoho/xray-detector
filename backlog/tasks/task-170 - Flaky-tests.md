---
id: TASK-170
title: Flaky tests
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-20T15:18:00Z'
updated_date: '2026-11-20T16:25:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 306000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
tests/test_shortcuts.py är flaky under pytest-xdist: tre olika test fallerar från körning till körning. Behöver åtgärdas. 

Passa även på att gå igenom testsviten och kontrollera om det finns testfall som är meningslösa att köra. Det tar tid att köra testsviten så jag vill bara ha kvar meningsfulla testfall.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tests/test_shortcuts.py fallerar inte längre under pytest -n 4; upprepade körningar ger samma resultat
- [x] #2 Alla tangenttryck i test_shortcuts.py går genom en hjälpare som sätter Qt:s aktiva fönster, så testerna inte beror på skrivbordets förgrund
- [x] #3 Testfall som är dubbletter, tautologier eller rena Qt-bekräftelser är borttagna och motiverade i uppgiften
- [x] #4 Hela sviten och ruff går igenom
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproducera flakiness i tests/test_shortcuts.py med pytest -n 4 och logga fönsteraktivering, fokus och genvägarnas läge vid varje tangenttryck.
2. Göra en press()-hjälpare som sätter Qt:s aktiva fönster med QApplication.setActiveWindow() och skickar tangenten till fönstrets fokuswidget, så testerna inte längre hänger på skrivbordets förgrund.
3. Låta alla tangenttryck i test_shortcuts.py gå genom press(), även dialogtesterna.
4. Granska sviten fil för fil och ta bort testfall som är dubbletter, tautologier eller rena Qt-bekräftelser.
5. Verifiera med upprepade pytest -n 4-körningar, ruff och hela sviten.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Orsak: Qt kör genvägar och mnemonik bara i det aktiva fönstret. activateWindow() går via skrivbordet, och under pytest-xdist kämpar fyra processer om förgrunden, så fönstret kunde tappa aktiveringen mitt i ett test. Loggning visade två lägen: active=False vid tangenttrycket, och active=True före men active=False direkt efter, eftersom keyClick() hann köra en väntande avaktiveringshändelse. Dialogtesterna hade samma fel: QTest.keyClick(dialog, ...) stänger bara dialogen när dialogen är aktiv.

Åtgärd: press()-hjälpare i tests/test_shortcuts.py som kör processEvents(), sätter Qt:s aktiva fönster med QApplication.setActiveWindow() och skickar tangenten till window.focusWidget(). Alla 20 tangenttryck går nu genom press(), inklusive de tre dialogtesterna. setActiveWindow() är markerad deprecated i Qt 6.12, så anropet ligger i en liten hjälpare med kommentar och en lokal varning-suppression; det är enda sättet att sätta Qt:s aktiva fönster utan skrivbordet.

Borttagna testfall (21 st, alla verifierade mot den kod de skulle skydda): test_style.py::test_training_start_button_is_as_high_as_abort och ::test_apply_metrics_leaves_untouched_measures_to_qt, test_busy_indicator.py::test_indicator_paints_spinner_and_text, test_settings_dialog.py::test_tab_row_has_four_tabs, test_translations.py::test_without_the_translation_qt_keeps_its_own_texts, test_colors.py::test_same_class_gets_the_same_color_every_time, test_app_config.py::test_yaml_overrides_model_and_threshold, test_annotation_navigation.py::test_annotation_tab_index_is_looked_up_from_the_tab_order, test_annotation_classes.py::test_clicking_the_class_label_selects_the_annotation, test_annotation_pan.py::test_the_middle_button_still_pans_in_draw_mode, test_tool_icons.py::test_the_maximize_and_restore_icons_are_drawn_at_the_requested_size, test_dataset_selection.py::test_click_selects_whole_capture och ::test_no_markerad_row_on_thumbnails, test_dataset_thumbnails.py::test_thumbnail_draws_the_annotations, test_dataset_variation_view.py::test_synthetic_icon_explains_the_variation, test_export_split.py::test_split_is_reproducible, test_detector_settings.py::test_base_detector_threshold_setter, test_resources.py::test_meter_sets_bar_and_text, test_video_source_persistence.py::test_title_row_shows_only_fps, test_training_pause.py::test_training_finish_restarts_the_streams, test_epoch_metrics.py::test_command_passes_the_overfitting_guard.

Rättat i stället för borttaget: test_training_history.py::test_the_evaluate_button_needs_a_checked_row skapade vyn utan dataset, så knappen var avstängd oavsett kryssruta och testet kunde inte fallera. Det skapar nu vyn med ett dataset och kräver att knappen tänds när raden markeras.

Behållet medvetet: frånvaro-kontroller som vaktar dokumenterade beslut (test_annotation_view_has_no_delete_button, test_classes_are_not_stored_in_the_settings, test_config_has_no_class_list_of_its_own), fallback- och felvägar, gränsvärden samt etikettkontroller som ingen annan test täcker.

Verifiering: 70 upprepade körningar av tests/test_shortcuts.py med -n 4 gav 0 fel (före åtgärden föll 1-4 tester i varje körning). Hela sviten: 1023 passed, 1 skipped med -n 4 i fem körningar i rad, 44 s. Snabba sviten med -m 'not slow': 781 passed, 1 skipped, 28 s. ruff check . utan anmärkning. Sviten gick från 1044 till 1023 testfall.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
tests/test_shortcuts.py är inte längre flaky. Orsaken var att Qt bara kör genvägar och mnemonik i det aktiva fönstret: activateWindow() går via skrivbordet, och under pytest-xdist kämpar fyra processer om förgrunden, så fönstret kunde tappa aktiveringen mitt i ett test. En ny press()-hjälpare sätter Qt:s aktiva fönster med QApplication.setActiveWindow() och skickar tangenten till fönstrets fokuswidget; alla tangenttryck i filen, även de tre dialogtesterna, går genom den. setActiveWindow() är deprecated i Qt 6.12 och ligger därför i en liten kommenterad hjälpare.

Testsviten är samtidigt genomgången och 21 testfall är borttagna: dubbletter (t.ex. test_split_is_reproducible, test_click_selects_whole_capture, test_title_row_shows_only_fps), tautologier (test_annotation_tab_index_is_looked_up_from_the_tab_order, test_same_class_gets_the_same_color_every_time) och rena Qt-bekräftelser (test_without_the_translation_qt_keeps_its_own_texts, test_tab_row_has_four_tabs). Ett test som passerade av fel anledning, test_the_evaluate_button_needs_a_checked_row, är rättat så att det faktiskt kräver en markerad rad. Frånvaro-kontroller som vaktar dokumenterade beslut, fallback- och felvägar samt gränsvärden är kvar.

Verifiering: 70 upprepade körningar av tests/test_shortcuts.py med -n 4 utan fel (före åtgärden föll 1-4 tester per körning). Hela sviten 1023 passed, 1 skipped med -n 4 i fem körningar i rad, cirka 44 s; snabba sviten med -m 'not slow' 781 passed, 1 skipped på 28 s. ruff check . utan anmärkning. Sviten gick från 1044 till 1023 testfall, så körtiden är i stort sett oförändrad: de borttagna testerna var billiga, och de dyra är MainWindow-testerna som är kvar. docs/arkitektur.md förklarar nu varför tangenttrycken går genom press().
<!-- SECTION:FINAL_SUMMARY:END -->

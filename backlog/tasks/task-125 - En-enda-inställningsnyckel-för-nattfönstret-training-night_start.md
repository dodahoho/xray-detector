---
id: TASK-125
title: En enda inställningsnyckel för nattfönstret (training/night_start)
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:50:00Z'
updated_date: '2026-11-17T22:11:00Z'
labels:
  - bugfix
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - xray_detector/domain/training.py
  - xray_detector/application/training_service.py
  - xray_detector/ui/settings_dialog.py
  - xray_detector/ui/training_view.py
  - tests/test_settings_dialog.py
priority: high
type: bug
ordinal: 176000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TrainingScheduleSection._save_clock skriver både training/night_start_hour (int) och training/night_start ("HH:00"); TrainingView._on_start läser strängvarianten, TrainingScheduleSection int-varianten och TrainingScheduler har egna defaultvärden (23:00/05:00). Tre ställen för ett värde som kan glida isär tyst (review_vibe_deepseek41_flash.md P1.2). Använd en nyckel "HH:MM" med parse_clock/format_clock i domain/ som vy, dialog och schemaläggare delar; migrera _hour-nycklarna i restore_settings.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Endast training/night_start ("HH:MM") används av vy, dialog och schemaläggare
- [x] #2 Gamla _hour-nycklar migreras eller hanteras säkert i restore_settings
- [x] #3 Befintliga inställningar (23:00/05:00) fungerar oförändrade efter migrering
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
1. Lägg NIGHT_START_KEY/NIGHT_END_KEY, NIGHT_START_DEFAULT/NIGHT_END_DEFAULT samt parse_clock/format_clock i domain/training.py.

2. Låt TrainingScheduler, TrainingScheduleSection och TrainingView._on_start använda samma nycklar och hjälpare; ta bort schemaläggarens egen _parse_clock och de tre literala standardvärdena.

3. Migrera training/night_start_hour och training/night_end_hour i TrainingView.restore_settings: skriv om till HH:MM om den nya nyckeln saknas och ta bort den gamla.

4. Uppdatera test_settings_dialog.py och lägg till tester för migreringen och för att vyn köar med samma nycklar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
domain/training.py äger nu nattfönstret: NIGHT_START_KEY/NIGHT_END_KEY (training/night_start, training/night_end), NIGHT_START_DEFAULT/NIGHT_END_DEFAULT (23:00/05:00) samt parse_clock(value, fallback) och format_clock(time). TrainingScheduler använder dem i stället för sin egen _parse_clock och sina egna defaultvärden; queue_job tar tom sträng som default och faller tillbaka på det aktuella värdet. TrainingScheduleSection skriver bara HH:MM-nyckeln (timmen från spinboxen, minuterna 00) och läser timmen med parse_clock. TrainingView._on_start skickar vidare det sparade värdet utan egen fallback.

Migreringen ligger i TrainingView.restore_settings -> _migrate_night_window, som MainWindow anropar vid uppstart innan dialogen kan öppnas. Den använder settings.contains() i stället för value(key, type=str) is None, eftersom PySide6 ger tom sträng i stället för None för en saknad nyckel med type=str - första försöket skrev därför aldrig den nya nyckeln.

Verifiering: 30 tester i test_settings_dialog.py och test_training_scheduler.py går igenom, däribland migreringen (22/6 -> 22:00/06:00, gamla nycklar borta), att en redan sparad HH:MM-nyckel vinner över _hour-nyckeln, och att vyn köar ett nattjobb med 01:15/04:45 från samma nycklar. Hela sviten: 864 passed, 1 skipped, 4 failed - samma fyra Windows-specifika offscreen-fel som förut. ruff utan anmärkning.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Nattfönstret har nu en källa: training/night_start och training/night_end med värdet HH:MM, ägda av domain/training.py tillsammans med parse_clock, format_clock och standardvärdena 23:00/05:00. Schemaläggaren, inställningssektionen och träningsvyn läser och skriver samma nycklar, så de kan inte längre glida isär. De gamla _hour-nycklarna migreras en gång i TrainingView.restore_settings och tas bort; en redan sparad HH:MM-nyckel vinner. Verifierat med 30 tester i test_settings_dialog.py och test_training_scheduler.py samt hela sviten (864 passed, 1 skipped, inga nya fel).
<!-- SECTION:FINAL_SUMMARY:END -->

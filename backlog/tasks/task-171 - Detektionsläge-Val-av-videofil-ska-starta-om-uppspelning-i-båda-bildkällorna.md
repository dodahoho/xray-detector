---
id: TASK-171
title: Detektionsläge - Val av videofil ska starta om uppspelning i båda bildkällorna
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-20T17:30:00Z'
updated_date: '2026-11-20T17:33:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/infrastructure/video/source.py
  - xray_detector/ui/detection_view.py
  - tests/test_video_file_sync.py
  - docs/beteende.md
type: enhancement
ordinal: 463000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När en videofil väljs som en bildkälla och den andra bildkällan redan har en videofil vald så ska uppspelningen av de bäda videofilerna synkas, dvs startas från början samtidigt. 

Detta pga att videofiler väljs så att de visar samma innehål fast från två olika vinklar och då vill man att uppspelningspositionen i videon ska vara samma i de bäda bildkällorna.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 När en videofil väljs i en panel och den andra panelen redan spelar en videofil startar båda om från första ramen samtidigt.
- [x] #2 De två filerna håller samma uppspelningsposition, så samma ögonblick syns i båda bildkällorna.
- [x] #3 En UVC-kamera eller tom källa i den andra panelen påverkas inte av filvalet.
- [x] #4 docs/beteende.md beskriver att de två videofilerna startar om tillsammans.
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
1. FileSource får en valfri gemensam starttid (start_at) som sätter första deadlinen, så två videofiler börjar på samma absoluta tidpunkt.
2. build_source skickar starttiden vidare till FileSource.
3. DetectionView._on_source_requested startar om båda filkällorna med samma starttid när den andra panelen redan spelar en videofil.
4. Nya tester i tests/test_video_file_sync.py.
5. docs/beteende.md beskriver att de två videofilerna startar om tillsammans.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
FileSource tar en valfri start_at (perf_counter-tid) som sätter första deadlinen, och read() öppnar källan innan den väntar så ramtiden och starttiden är kända för första ramen. build_source skickar starttiden vidare. DetectionView._start_file_sources ger den valda filen och den andra panelens fil samma starttid 100 ms framåt, så båda hinner öppnas; en UVC-källa i den andra panelen rörs inte.

Verifiering: tests/test_video_file_sync.py (7 tester) plus hela sviten: 1030 passed, 1 skipped. Negativ kontroll med två StreamWorker på samma fil där den andra startas 100 ms senare: utan gemensam starttid 99,5 ms isär, med gemensam starttid 0,0 ms isär. ruff check . är ren; ruff format --check flaggar en rad i detection_view.py som redan fanns i HEAD och lämnades orörd.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Val av videofil startar nu om båda bildkällorna synkroniserat. FileSource tar en valfri start_at som sätter första deadlinen, och read() öppnar källan innan den väntar så ramtiden och starttiden är kända redan för första ramen. build_source skickar starttiden vidare. DetectionView._start_file_sources ger den valda filen och den andra panelens fil samma starttid 100 ms framåt, så båda hinner öppnas innan första ramen; en UVC-källa eller tom källa i den andra panelen rörs inte.

Verifiering: tests/test_video_file_sync.py (7 tester) och hela sviten (1030 passed, 1 skipped). Negativ kontroll med två StreamWorker på samma fil där den andra startas 100 ms senare gav 99,5 ms isär utan gemensam starttid och 0,0 ms isär med. ruff check . är ren.

Kvar att känna till: starttiden är 100 ms framåt, så en fil som tar längre tid än så att öppna (till exempel på en långsam nätverksenhet) faller tillbaka på att börja spela direkt och då inte exakt i takt. Uppspelningen synkas vid val, återställning vid start och återupptagning efter träning; filerna loopar var för sig och kan glida isär igen efter ett varv om de har olika längd.
<!-- SECTION:FINAL_SUMMARY:END -->

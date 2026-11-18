---
id: TASK-149
title: 'Prestanda: skala ner och cacha tumnaglar i DatasetView-arbetstråden'
status: Done
assignee: []
created_date: '2026-11-17T20:54:00Z'
updated_date: '2026-11-18T08:10:00Z'
labels:
  - performance
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
priority: low
type: enhancement
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
DatasetView._load läser varje bild i full upplösning till RAM vid varje refresh (~6-8 GB för 1000 bilder) bara för 170 px tumnaglar, och läser om alla bilder vid varje sparad annotering (utvärdering_argon.md §5.1, endast argon). Skala ner QImage till THUMB_HEIGHT redan i arbetstråden (QImage/QPainter är trådsäkra) och cacha tumnaglar i minnet eller under datasets/.thumbs/ indexerat på (image_id, mtime, annotations).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 1000 bilder i datasetet använder ~150 MB istället för ~8 GB RAM vid visning
- [x] #2 Refresh efter sparad annotering avkodar bara nya/ändrade bilder (cache träffar)
- [x] #3 Alla dataset-tester passerar
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
1. Skala ner bilden till THUMB_HEIGHT redan i DatasetView._load (QImage är trådsäker).
2. Cacha tumnaglarna i minnet på (bild-id, mtime) och släpp poster för bilder som lämnat datasetet.
3. Låt _thumbnail_pixmap rita annoteringarna på den färdiga tumnageln med originalhöjden ur metadata som skala.
4. Tester för nedskalning, cacheträffar och ny mtime.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Genomfört: _load dekoder bilden, skalar till THUMB_HEIGHT och lägger tumnageln i self._thumb_cache[(id, mtime_ns)]. Cachen ersätts vid varje omladdning, så bara bilder som finns kvar behåller sin tumnagel. _thumbnail_pixmap tar nu en färdig tumnagel plus originalhöjden ur dataset.json. Osparade fångster skalas också ner före QPixmap. Nya tester: test_thumbnails_are_scaled_down_in_the_worker, test_refresh_reuses_cached_thumbnails, test_a_changed_image_is_decoded_again.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
DatasetView._load skalar ner varje bild till THUMB_HEIGHT i arbetstråden och cachar tumnageln på (bild-id, mtime), så bara tumnaglarna ligger i minnet i stället för hela datasetet i full upplösning. En omladdning efter en sparad annotering träffar cachen och avkodar bara nya eller ändrade bilder; poster för borttagna bilder släpps. Annoteringsramarna ritas fortfarande efter nedskalningen med originalhöjden ur metadata som skala. Verifierat med uv run ruff check . och uv run pytest -q (893 passed, 1 skipped) samt tre nya tester.
<!-- SECTION:FINAL_SUMMARY:END -->

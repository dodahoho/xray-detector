---
id: TASK-150
title: 'Prestanda: skriv inte om PNG-filer vid redigering av annoteringar'
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
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När ett sparat bildpar redigeras konverteras bilden BGR->QImage->BGR och replace_samples skriver om PNG-filen med cv2.imwrite även fast bara rektanglar/klasser kan ändras (utvärdering_argon.md §5.4). Behåll original-frame i AnnotationCanvas och uppdatera bara .txt-labelfiler och dataset.json vid redigering.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Redigering av befintligt bildpar skriver inte om PNG-filen (mtime oförändrad)
- [x] #2 Labelfiler och metadata uppdateras korrekt (tester passerar)
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
1. Låt AnnotationCanvas behålla originalramen i BGR och returnera den ur result() i stället för att konvertera QImage -> BGR.
2. Låt DatasetStore.replace_samples skriva bara label-filer och dataset.json; bredd och höjd finns i metadata.
3. Test som jämför bildfilens mtime före och efter en redigering.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Genomfört: canvasen har self.frame (BGR) satt i load_frame och nollställd tillsammans med self.image; result() returnerar den orörda ramen. replace_samples skriver label-filer via write_labels och sparar metadata, utan cv2.imwrite. Fallbacken till delete+add vid antalsmismatch är kvar och skriver bilder som förut. Nytt test: test_replace_samples_leaves_the_png_file_untouched jämför st_mtime_ns.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
AnnotationCanvas behåller originalramen i BGR, så en sparning slipper konvertera bilden fram och tillbaka. DatasetStore.replace_samples skriver bara label-filerna och dataset.json; PNG-filen lämnas orörd och dess mtime är oförändrad, vilket ett nytt test verifierar. Verifierat med uv run ruff check . och uv run pytest -q (893 passed, 1 skipped).
<!-- SECTION:FINAL_SUMMARY:END -->

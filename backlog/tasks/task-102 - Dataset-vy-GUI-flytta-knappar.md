---
id: TASK-102
title: Dataset vy - GUI flytta knappar
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T20:52:00Z'
updated_date: '2026-11-16T21:15:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 366000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Flytta knapparna för att utöka/återställa dataset till höger sida men ha ett mellanrum till knapparna för att exportera dataset så att utöka/återställ ändå upplevs som en egen knappgrupp
<!-- SECTION:DESCRIPTION:END -->

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
1. Lägg en stretch först i datasetvyns knapprad så hela raden hamnar till höger.
2. Lägg Utöka/Återställ först i den högra gruppen och sätt ett fast mellanrum (addSpacing) före exportknapparna, så utöka/återställ upplevs som en egen knappgrupp.
3. Verifiera med sviten (test_shortcuts, test_busy_operations, test_dataset_variation_view).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Knappraden i datasetvyn börjar nu med en stretch, så hela raden ligger till höger. Utöka med bildvariationer och Återställ till original står först i den högra gruppen och följs av BUTTON_GROUP_GAP (24 px) innan Exportera COCO, Exportera YOLO, Ta bort markerade och Inställningar.

Mätt i ett 1600 px brett fönster: 6 px mellan knapparna inom en grupp och 30 px mellan utöka/återställ och exportknapparna (24 px spacing + 6 px layoutavstånd). Ett nytt test i tests/test_dataset_variation_view.py låser ordningen och mellanrummet.

Verifiering: hela sviten gick igenom (770 passed, 1 skipped), ruff check på de ändrade filerna gav inga fel, och vyn renderades och mättes upp.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Knapparna för att utöka och återställa datasetet ligger nu till höger i datasetvyn, i en egen grupp med 24 px luft till exportknapparna. Raden är högerställd, så grupperingen syns både i koden (BUTTON_GROUP_GAP) och i det renderade gränssnittet: 6 px inom en grupp och 30 px mellan de två grupperna.

Verifiering: hela sviten gick igenom (770 passed, 1 skipped) med ett nytt test som låser ordningen och mellanrummet, ruff check på de ändrade filerna gav inga fel, och vyn renderades och mättes upp i ett 1600 px brett fönster.
<!-- SECTION:FINAL_SUMMARY:END -->

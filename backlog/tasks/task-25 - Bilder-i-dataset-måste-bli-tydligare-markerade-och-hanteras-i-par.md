---
id: TASK-25
title: Bilder i dataset måste bli tydligare markerade och hanteras i par
status: Done
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T08:00:00Z'
updated_date: '2026-11-10T08:19:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
I vyn Dataset kan man markera bilder och trycka knapp för att ta bort markerade bilder. Nu är det väldigt otydligt eller inte alls synligt vilka bilder som är markerade eller ej.

Bilder bör alltid hanteras som ett par. Det behöver inte gå att markera enskilda bilder, alltid gruppen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ett klick på en bild markerar hela fångsten (paret), inte en enskild bild
- [x] #2 Markeringen är tydligt synlig i datasetvyn
- [x] #3 Borttagningsknappen visar antal markerade bilder och är avstängd när inget är markerat
- [x] #4 Borttagning av en markerad fångst tar bort alla bilder i fångsten
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Datasetvyn: klick på en bild markerar hela fångsten (paret) i stället för en enskild bild; osparade fångster hanteras som grupp på samma sätt.
2. Tydlig markering: kraftigare ram, tonad bakgrund och en MARKERAD-badge på varje bild i fångsten.
3. Borttagningsknappen visar antal markerade bilder och är avstängd när inget är markerat.
4. _on_delete deduplicerar osparade grupp-id:n och räknar bilder, inte grupper.
5. Tester: gruppmarkering, avmarkering, knappens läge och borttagning av hela paret.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Datasetvyn markerar nu hela fångsten: _on_thumb_clicked togglar alla thumbnails med samma group_id (sparade via _groups, osparade via pending-flaggan) i stället för en enskild bild. Markeringen är tydligare: 4 px ram i #4da3ff, tonad bakgrund #1d3b57 och en MARKERAD-badge överst på varje bild i paret. Borttagningsknappen visar antal markerade bilder och är avstängd när inget är markerat. _on_delete deduplicerar osparade grupp-id:n (annars hade remove_pending anropats en gång per bild) och räknar bilder i stället för grupper; _selected_ids togs bort som död kod.

Verifiering: 7 nya tester i tests/test_dataset_selection.py (gruppmarkering, avmarkering, knappens läge och text, synlig markering, borttagning av hela paret, borttagning utan markering, osparad fångst). Hela sviten 119 passed, 1 skipped. Rendering offscreen: 0 accentfärgade pixlar före markering och 5892 efter, båda bilderna i paret får badge och knappen visar 'Ta bort markerade (2)'.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Bilder i datasetvyn hanteras nu alltid som en fångst: ett klick markerar hela paret, både för sparade och osparade fångster, och markeringen syns tydligt med kraftigare ram, tonad bakgrund och en MARKERAD-badge på varje bild. Borttagningsknappen visar antal markerade bilder och är avstängd när inget är markerat, och borttagning tar bort alla bilder i fångsten.

Verifierat: 7 nya tester; hela sviten 119 passed, 1 skipped. Offscreen-rendering visar 0 accentfärgade pixlar före markering och 5892 efter, med badge på båda bilderna och knapptexten 'Ta bort markerade (2)'.
<!-- SECTION:FINAL_SUMMARY:END -->

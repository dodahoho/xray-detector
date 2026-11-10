---
id: TASK-25
title: Bilder i dataset måste bli tydligare markerade och hanteras i par
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T08:00:00Z'
updated_date: '2026-11-10T08:13:00Z'
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
- [ ] #1 Ett klick på en bild markerar hela fångsten (paret), inte en enskild bild
- [ ] #2 Markeringen är tydligt synlig i datasetvyn
- [ ] #3 Borttagningsknappen visar antal markerade bilder och är avstängd när inget är markerat
- [ ] #4 Borttagning av en markerad fångst tar bort alla bilder i fångsten
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Datasetvyn: klick på en bild markerar hela fångsten (paret) i stället för en enskild bild; osparade fångster hanteras som grupp på samma sätt.
2. Tydlig markering: kraftigare ram, tonad bakgrund och en MARKERAD-badge på varje bild i fångsten.
3. Borttagningsknappen visar antal markerade bilder och är avstängd när inget är markerat.
4. _on_delete deduplicerar osparade grupp-id:n och räknar bilder, inte grupper.
5. Tester: gruppmarkering, avmarkering, knappens läge och borttagning av hela paret.
<!-- SECTION:PLAN:END -->

---
id: TASK-106
title: Dataset - Utöka dataset med bildvariationer
status: To Do
assignee: []
created_date: '2026-11-16T21:12:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 104000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Önskar lite ändrad funktion för att utöka med bildvariationer.

I dialogen ytöka med bildvariationer ställer man in hur många syntetiska bilder man vill skapa av varje bildpar. Därefter aktiverar man vilka typer av bildvariationer man vill göra samt inställningar för de aktiverade typerna.

Exempel: 
5st bildvariationer
Aktivera de typer som ska användas av rotation, vändning, storlek, färg
Om rotation är aktiverat går det att ställa in vinkel, annars disabled
Samma för vändning, storlek och färg.

När sedan bildvariationerna ska skapas finns en till inställning som anger om man ska: 
* skapa en bild per typ av aktiverad variation
* skapa bilder med samtliga aktiverade variationer
* skapa bilder med slumpvisa variationer (väljer bara bland de aktiverade typerna och dess inställningar)

Om slumpvida variationer är valda slumpas det bland de aktiverade funktionerna vilka som ska användas och med hur mycket (inom valt intervall)
T ex om rotation, vändning och storlek är aktiverade så kan en syntetiserad bild endast ha rotation, en annan syntetiserad bild har alla tre typerna samtidigt och en tredje bild har typerna vänding vertikalt och storleksändring.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

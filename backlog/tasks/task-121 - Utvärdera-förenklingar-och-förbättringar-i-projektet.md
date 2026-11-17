---
id: TASK-121
title: Utvärdera förenklingar och förbättringar i projektet
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-17T15:16:00Z'
updated_date: '2026-11-17T18:21:00Z'
labels: []
dependencies: []
type: task
ordinal: 119000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Utvärdera projektet och ge förslag på hur det (koden, strukturen, arkitekturen, val av ramverk, gui, dokumentation, etc.) kan förbättras (göras enklare, effektivare, mer förvaltningsbart, ta bort död/gammal kod, undvika deprecations, undvika duplicering och parallella implementationer/definitioner av liknande saker, m.m.). Spara utvärderingen i en markdown-fil "review_vibe_deepseek41_flash.md".
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Läs igenom hela kodbasen (domain, application, infrastructure, ui) samt tester och dokumentation.
2. Kör tester och ruff för att få objektivt underlag.
3. Identifiera konkreta förbättringsområden: död/duplicerad kod, parallella implementationer, lagerläckage, deprecations, GUI-struktur, dokumentation.
4. Skriv utvärderingen till review_vibe_deepseek41_flash.md med prioriterade, åtgärdbara förslag.
5. Verifiera DoD och markera uppgiften klar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Genomfört en full genomläsning av xray_detector/ (11 575 rader, samtliga moduler i domain, application, infrastructure och ui), tests/ (71 filer), README.md, specs.md och pyproject.toml. Utvärderingen ligger i review_vibe_deepseek41_flash.md (464 rader).

Underlag som verifierats, inte antagits:
- pytest: 861 passed, 1 skipped in 270.41s (baslinje före och efter, ingen kod ändrad).
- ruff default (E4/E7/E9/F): 55 fel, 33 automatiskt fixbara. Utökad regeluppsättning: 231 fel, varav 102 E501 och 43 PLC0415.
- AST-skanning efter oanvända modulnivådefinitioner: 6 döda symboler i produktionskoden plus 1 oanvänd import och 1 oanvänd variabel.
- Reproducerat P1.1: en trasig dataset.json ger JSONDecodeError ur DatasetService.image_pair_count(), som anropas från MainWindow._log_startup() i __init__ – appen startar inte.
- Varje file:line-referens i rapporten är kontrollerad mot källan.

Rapporten är disponerad som P1 (fel/risker), P2 (duplicering), P3 (städning), följt av struktur, verktyg/deprecations, GUI, dokumentation, testsvit och en prioriterad åtgärdsplan med 20 punkter. Avsnitt 10 anger vad som medvetet inte föreslås (ramverksbyte, formatbyte, stor UI-refaktorering) med skälen.

Ingen produktionskod ändrades – uppgiften var att utvärdera och dokumentera.
<!-- SECTION:NOTES:END -->

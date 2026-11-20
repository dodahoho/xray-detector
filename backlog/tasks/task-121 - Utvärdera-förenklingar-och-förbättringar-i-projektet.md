---
id: TASK-121
title: Utvärdera förenklingar och förbättringar i projektet
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T15:16:00Z'
updated_date: '2026-11-17T18:22:00Z'
labels: []
dependencies: []
type: task
ordinal: 347000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Utvärdera projektet och ge förslag på hur det (koden, strukturen, arkitekturen, val av ramverk, gui, dokumentation, etc.) kan förbättras (göras enklare, effektivare, mer förvaltningsbart, ta bort död/gammal kod, undvika deprecations, undvika duplicering och parallella implementationer/definitioner av liknande saker, m.m.). Spara utvärderingen i en markdown-fil "review_vibe_deepseek41_flash.md".
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

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Utvärderingen ligger i review_vibe_deepseek41_flash.md (464 rader, 20 prioriterade åtgärder). Ingen produktionskod ändrades – uppgiften var att utvärdera och dokumentera.

Vad rapporten kommer fram till:
- Projektet är i gott skick: lagren finns, 862 tester passerar, och kommentarerna förklarar besluten. Det som håller tillbaka det är duplicering, för stora vyer och avsaknaden av en grind.
- P1 (fel/risker): en trasig dataset.json kastar JSONDecodeError ur DatasetStore._load_metadata och kraschar appen vid start (reproducerat); nattfönstret har två nycklar som synkas för hand; num_objects underhålls inkrementellt på fyra ställen; main_window styr annoteringsfliken via magiskt tab-index 1 på tio ställen och anropar AnnotationView._on_save() utifrån.
- P2 (duplicering): training_manifest.json läses av två moduler med var sin tolkning; data.yaml parsas två gånger där train_task-varianten är en delmängd som ger tom klasslista i manifestet; fångstgruppering finns i fyra varianter där tre räknar fel för syntetiska bilder; enhetsstatus, IoU, bildskrivning och färger är också duplicerade.
- P3 (städning): 6 döda symboler, tests/prototype/ (spike från TASK-21 som fortfarande körs), runs/-rester i git, 38 MB video i git, README som refererar borttagna PLAN.md.
- Verktyg: ruff är oconfigurerat (55 fel i default-läget), ingen CI finns, tidsstämplar blandar lokal tid och UTC.

Rekommenderad ordning: sätt [tool.ruff] och en CI-workflow först (en dag), sedan P1-punkterna, sedan städningen. Avsnitt 10 anger vad som medvetet inte föreslås: ramverksbyte, datasetformatbyte och en stor UI-refaktorering utan CI.

Verifiering: pytest 861 passed, 1 skipped in 270.41s. ruff default 55 fel / utökad 231. AST-skanning för döda symboler. Reproducerat startkraschen. Varje file:line-referens kontrollerad mot källan.

Uppföljning: rapportens 20 punkter är inte skapade som Backlog-tasks – det kräver godkännande enligt projektets regler.
<!-- SECTION:FINAL_SUMMARY:END -->

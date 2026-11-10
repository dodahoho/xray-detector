---
id: TASK-26
title: Lägg till fler RF-DETR modellstorlekar
status: Done
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T08:11:00Z'
updated_date: '2026-11-10T08:16:00Z'
labels: []
dependencies: []
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
RF-DETR finns i fler storlekar än small. Lägg till i applikationen
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Modellväljaren i detektions- och träningsläget erbjuder RF-DETR nano, small, medium och large
- [x] #2 Vald storlek styr vilken rfdetr-klass som laddas vid inferens och träning
- [x] #3 Utan rfdetr-paketet är samtliga RF-DETR-poster avstängda
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
1. Modellregistret: lägg till rfdetr-nano, rfdetr-medium och rfdetr-large bredvid rfdetr-small.
2. RfDetrDetector: mappa modellnyckel -> rfdetr-klass (RFDETRNano/Small/Medium/Large) i stället för hårdkodad RFDETRSmall.
3. train_task._train_rfdetr: använd samma mappning så träningen kör vald storlek (args.weights).
4. Tester: mappning för alla fyra nycklar, okänd nyckel ger ValueError, registret innehåller alla storlekar, detektorn använder rätt klass.
5. Verifiering: riktig inferens med nano på demoram samt offscreen-kontroll att väljaren listar alla storlekar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Modellregistret har nu rfdetr-nano/small/medium/large. RfDetrDetector använder rfdetr_variant(model_name) som mappar nyckel -> RFDETRNano/Small/Medium/Large via RFDETR_VARIANTS; okänd nyckel ger ValueError. train_task._train_rfdetr använder samma mappning på args.weights, så träningen kör vald storlek i stället för hårdkodad small.

Bugfix på vägen: _varkw refererade inspect som importerades lokalt i _train_rfdetr, så träningsgrenen kastade NameError så fort ett kwarg saknades i train()-signaturen. Importen ligger nu på modulnivå; felet upptäcktes av det nya testet för storleksvalet.

Verifiering: 7 nya tester (registret, mappningen för alla fyra nycklar, okänd nyckel, detektorns klassval, träningens klassval, båda vyernas listor). Hela sviten 112 passed, 1 skipped. Riktig inferens med rfdetr-nano på media/xray_slideshow_side.mp4 gav 49 detektioner vid tröskel 0.05. Offscreen-kontroll visar alla fyra posterna aktiverade i detektionsvyn och att mappningen slår upp RFDETRNano/Small/Medium/Large i det riktiga paketet. Medium och large är inte körda med riktiga vikter (nedladdning ~400-500 MB styck); de går genom samma kodväg som nano.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
RF-DETR erbjuds nu i nano, small, medium och large i både detektions- och träningsläget. RfDetrDetector mappar modellnyckel till rfdetr-klass via rfdetr_variant() (RFDETR_VARIANTS) i stället för hårdkodad RFDETRSmall, och träningsgrenen använder samma mappning på args.weights så vald storlek styr både inferens och träning. Okänd nyckel ger ValueError med tydligt meddelande.

På vägen hittades och fixades en latent bugg: _varkw i train_task.py refererade inspect som bara importerades lokalt i _train_rfdetr, så RF-DETR-träning kastade NameError när ett kwarg saknades i train()-signaturen.

Verifierat: 112 passed, 1 skipped; riktig inferens med nano gav 49 detektioner vid tröskel 0.05; offscreen-kontroll visar alla fyra poster aktiverade och korrekt klassuppslag. Medium/large är inte körda med riktiga vikter (stor nedladdning) men delar kodväg med nano.
<!-- SECTION:FINAL_SUMMARY:END -->

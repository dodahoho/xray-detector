---
id: TASK-26
title: Lägg till fler RF-DETR modellstorlekar
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T08:11:00Z'
updated_date: '2026-11-10T08:13:00Z'
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
- [ ] #1 Modellväljaren i detektions- och träningsläget erbjuder RF-DETR nano, small, medium och large
- [ ] #2 Vald storlek styr vilken rfdetr-klass som laddas vid inferens och träning
- [ ] #3 Utan rfdetr-paketet är samtliga RF-DETR-poster avstängda
<!-- AC:END -->

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
1. Modellregistret: lägg till rfdetr-nano, rfdetr-medium och rfdetr-large bredvid rfdetr-small.
2. RfDetrDetector: mappa modellnyckel -> rfdetr-klass (RFDETRNano/Small/Medium/Large) i stället för hårdkodad RFDETRSmall.
3. train_task._train_rfdetr: använd samma mappning så träningen kör vald storlek (args.weights).
4. Tester: mappning för alla fyra nycklar, okänd nyckel ger ValueError, registret innehåller alla storlekar, detektorn använder rätt klass.
5. Verifiering: riktig inferens med nano på demoram samt offscreen-kontroll att väljaren listar alla storlekar.
<!-- SECTION:PLAN:END -->

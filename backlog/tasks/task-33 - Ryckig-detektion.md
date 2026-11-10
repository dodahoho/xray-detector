---
id: TASK-33
title: Ryckig detektion
status: To Do
assignee: []
created_date: '2026-11-10T12:28:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
I detektionsläge blir det ryckig detektion. Ett detekterat objekt kan markeras i några frames och sedan forsvinna för att återigen dyka upp efter någon frame. Det variera också lite från frame till frame exakt var rektangeln är positionerad och vilken storlek den har. Det ger ett ryckigt intryck. Har YOLO eller RF-DETR något för att ge en mer smooth upplevelse?

Hur kan man annars göra så att det upplevs mindre ryckigt men ändå följer med objekten när de rullar på ett löpande band?
- ha en tröskel för detekterat objekt så att det behöver vara detekterat i ett antal kontinuerliga frames innan visning? hur gör man det när det flyttas i bilden?
- fade in/fade ut av detektionsrutor för mindre ryckighet?
- annat?
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

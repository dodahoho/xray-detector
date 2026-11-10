---
id: TASK-33
title: Ryckig detektion
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T12:28:00Z'
updated_date: '2026-11-10T12:50:00Z'
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

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Orsaken till ryckigheten är mätt och dokumenterad
- [ ] #2 Möjliga åtgärder är utvärderade med mätvärden
- [ ] #3 En rekommenderad åtgärd är vald och planerad
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
1. Utredning klar: fladder kommer från detektioner nära confidence-tröskeln, darr från modellens osäkerhet på rutans storlek.
2. Rekommenderad åtgärd: egen EMA + hysteres i StreamWorker (per ström, ingen ny dependency, fungerar för YOLO och RF-DETR).
3. Alternativ: ultralytics ByteTrack (jämnare storlek men kräver modellinstans per ström och fungerar inte för RF-DETR).
4. Komplement: fade in/ut i overlayn, bygger på samma identitet.
5. Implementera valt alternativ med tester och mätning före/efter.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Utredning på demovideorna (1280x720@30 fps, YOLO26m, tröskel 0.4, 150 ramar).

MÄTT FLADDER: 97 detektioner totalt, 8 av dem under confidence 0.5 (nära tröskeln 0.4) — det är de som slår av och på. Antalet detektioner per ram ändras i 15 av 119 rampar.

MÄTT DARR: för par med exakt en detektion i båda ramarna (n=80) flyttas mittpunkten 8,2 px i median (p95 11,2) och bredden ändras 3,0 px i median (p95 14,0). Positionsdelen är till stor del objektets verkliga rörelse; storleksdelen är modellens osäkerhet.

VAD YOLO/RF-DETR ERBJUDER:
- Ultralytics har inbyggd tracking (ByteTrack/BoT-SORT) via model.track(persist=True). Mätt: bredddarret faller från 2,96 till 0,62 px i median (-79 %) och p95 från 14,0 till 9,2 (-34 %), mittpunkten är oförändrad, kostnaden är +0,77 ms/ram (+13 %). Trackern ger också stabila id:n (ett id höll 86 ramar i följd).
- RF-DETR har ingen egen tracking. supervisions ByteTrack finns inte längre i supervision 0.31 (trackers flyttades ut), så den vägen kräver ett nytt beroende.
- Ultralytics-trackern har state per modellinstans. Appen delar en detektor mellan båda strömmarna, så tracking skulle blanda ihop dem — det kräver en modellinstans per ström (2x VRAM).

EGEN PROTOTYP (EMA + hysteres, ingen ny dependency, fungerar för båda modellerna): matcha detektioner mot spårade rutor med IoU > 0,3, jämna ut rutan med EMA och behåll en track i N missade ramar innan den släcks. Mätt med alpha 0,5 och 3 missade ramar: bredddarret 2,96 -> 1,38 px i median (-53 %), p95 14,0 -> 10,2 (-27 %), mittpunktens p95 11,2 -> 9,7 (-13 %), antalsbyten 15 -> 7 (-53 %). Alpha 0,35 jämnar mer men släpar mer.

REKOMMENDATION: egen EMA + hysteres i StreamWorker (per ström, ingen delad state, ingen ny dependency, fungerar för YOLO och RF-DETR). Ultralytics-trackern ger något jämnare storlek men kräver modellinstans per ström och fungerar inte för RF-DETR. Fade in/ut i overlayn är ett komplement som bygger på samma identitet.

AVVÄGNING: EMA och hysteres inför en fördröjning på cirka en ram plus två ramar innan en ny ruta visas. På ett löpande band är det 30-60 ms, vilket är försumbart, men det är en produktfråga.
<!-- SECTION:NOTES:END -->

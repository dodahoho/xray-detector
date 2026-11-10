---
id: TASK-24
title: Byte av modell till RF-DETR misslyckas
status: In Progress
assignee:
  - '@vibe-deepseek41'
created_date: '2026-11-10T07:34:00Z'
updated_date: '2026-11-10T07:39:00Z'
labels: []
dependencies: []
type: bug
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Om man byter modell i detektionsläge från t ex YOLO26 small till RF-DETR base verkar det inte fungera.

Felmeddelande i statusbar:
"Kunde inte ladda modell: No module named 'rfdetr'"
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Modellbyte ska få igång detektion med den valda modellen
- [ ] #2 Inget fel ska visas i statusbar
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Applikationen fungerar
- [ ] #2 Tester fungerar
- [ ] #3 Ändringar commitade
- [ ] #4 Dokumentation uppdaterad
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. RfDetrDetector: tolka supervision.Detections (xyxy/class_id/confidence) i stallet for dict-formatet, BGR->RGB fore predict, och ett tydligt fel nar rfdetr-paketet saknas.
2. DetectionView.refresh_models: avstang RF-DETR-posten och mark den '(rfdetr ej installerat)' nar paketet saknas, samma monster som tranningsvyn (TASK-11).
3. DetectionView: falla tillbaka till en tillganglig modell nar sparat val eller config.default_model pekar pa en otillganglig modell, sa ingen felladdning nar statusbaren.
4. Tester: detektorparsning mot fejkad Detections-klass (kraver inget paket) samt detektionsvyns avstangning och fallback.
5. Installera rfdetr-extra (uv sync --extra cu128 --extra rfdetr) och verifiera riktig inferens pa en demoram.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rotorsak: två separata fel. (1) rfdetr är ett valfritt extra som inte var installerat, och detektionsvyn saknade den avstängning som träningsvyn redan har (TASK-11), så valet gick rakt in i ImportError. (2) RfDetrDetector.detect parsade predict()-svaret som en dict (result.get("boxes")), men rfdetr returnerar supervision.Detections med xyxy/class_id/confidence — även med paketet installerat hade detektionen fallerat.

Ändringar: RfDetrDetector konverterar BGR->RGB, läser Detections-fälten och använder modellens egna klassnamn (data["class_name"]) med appens klasslista som fallback. DetectionView.refresh_models avstänger RF-DETR-posten och märker den "(rfdetr ej installerat)" när paketet saknas; _select_model används av __init__ och restore_settings så att ett sparat otillgängligt val faller tillbaka på en tillgänglig modell i stället för att försöka laddas.

Verifiering: 4 nya tester i tests/test_rfdetr.py (parsning mot fejkad Detections, avstängd post utan paket, aktiverad post med paket, fallback från sparat rfdetr-val). Hela sviten: 105 passed, 1 skipped (träningsvyns avstängningstest hoppar nu när rfdetr är installerat). Riktig inferens på media/xray_slideshow_side.mp4: modellen laddas och detect() ger 24 detektioner vid tröskel 0.05 utan undantag. GUI-körning offscreen: val av RF-DETR base gav RfDetrDetector och statusmeddelandet "Modell laddad: RF-DETR base", inget "Kunde inte ladda modell".

Miljö: rfdetr-extra installerat med uv sync --extra cu128 --extra rfdetr (28 paket, uv.lock oförändrad).
<!-- SECTION:NOTES:END -->

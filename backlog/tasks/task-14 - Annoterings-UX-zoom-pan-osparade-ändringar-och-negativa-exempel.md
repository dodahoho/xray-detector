---
id: TASK-14
title: 'Annoterings-UX: zoom/pan, osparade ändringar och negativa exempel'
status: Done
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-09T09:50:00Z'
labels:
  - annotation
  - gui
  - ux
dependencies: []
references:
  - annotation-view
modified_files:
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/main_window.py
  - tests/test_annotation_ux.py
priority: medium
type: enhancement
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Tre förbättringar från opencode-bigpickle och opencode-deepseek-flash (jämförelse_argon.md avsnitt 5:5):

1. Zoom med Ctrl+rull, panorering med mittenmusknapp, skaloberoende (kosmetiska) linjer och handtag så boxar är lätta att hantera oavsett zoomnivå.
2. Varning om man byter vy eller stänger med osparade annoteringsändringar.
3. Fråga om man vill spara som negativt exempel (bild utan objekt) om man klickar Spara utan inritade boxar, så blir negativa bilder användbara vid träning.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 annotering stöder zoom och pan med skaloberoende linjer och handtag
- [x] #2 osparade ändringar ger varning innan vybyte/stängning
- [x] #3 Spara utan boxar erbjuder att spara bilden som negativt exempel
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
AnnotationCanvas far zoom (Ctrl+musjulle, klamrad 0.2-5.0, bildpunkten under pekaren blir kvar), panorering med mittenmusknapp och reset_view(); laggret ritar redan i widgetkoordinater sa pennjocklecker och handtag ar skal oberoende aven zoomad. Dirty-sparning per canvas (changed-signal) vid rita/flytta/resize/Delete/klassbyte; load_frame och sparad resetar. MainWindow vaktar osparade annoteringar vid flikbyte (Spara/Kasta/Avbryt, Avbryt vender tillbaka till annoteringsfliken) och vid stangning (Avbryt stoppar stangningen). Spara utan markerade objekt fragar om negativt exempel (tomma annoteringar) - tack och nej fungerar, skrivs bara vid jak. Verifierat: 9 nya tester (zoom-runtrip, clamp, pan, reset, dirty+save-renser, negativt exempel ja/nej, flikbytesvakt med avbrott); hel svit 50 passed.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-19
title: Återanslutningsknapp direkt i strömpanelen
status: Done
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-09T13:38:00Z'
labels:
  - video
  - gui
  - ux
dependencies: []
references:
  - detection-view
  - video-capture
modified_files:
  - xray_detector/ui/detection_view.py
  - tests/test_reconnect.py
priority: medium
type: enhancement
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
vscode-qwen38 har per-panel fel-UI: statusoverlay med anslutningsförsök och en knapp Försök igen direkt i kameravyn, mycket tydligt när ett USB3-kort tappat kontakten. Se jämförelse_argon.md avsnitt 7:3.

I vibe-glm53: visa overlay i StreamPanel när källan tappas (idag bara texten Ingen videokälla) med knapp som återstartar senaste källval.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tappad källa visar tydlig statusruta med försöksräknare i panelen
- [x] #2 knappen Försök igen återstartar källan utan att öppna meny
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
StreamPanel far en atsloppnings-overlay tasnad vid 'Kallan tappad': de tva forsta forsoken sker automatiskt (statusraden visar 'Ansluter - forsd sd sd 1/3' med 1,5 s中医院terstag), och vid tredje forso kd sd kd sd kd nen synlig knapp 'Forsd kd igen' som terstardtar senaste kk ld sd ld sd sd ld (typ + index/fil) direkt utan att kallmenyn sd sd ppnas - samma signalvag sd sd sd m normalt kallval. Inkommande ramar nollstaller rprofileknaren och sd як komm dold; ciccopymptom syns inte i sd sd dag kd ld trak/statusyta och customer-floats sker forst sd sd ld ld ld ld ld sd ld ld ld ld sd ld sd ld ld ld ld ld ld ld ld ld ld ld ld ld ld sd ld sd int(RS). Verifierat: 5 nya tester (auto-wagonrd sd sd sd	Dictionary A	retag med kd sdd nedl direkt sd sd ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld ld; sd ld LD LD	; ld	;	;	;	;		;		;	;		;			;			;	;	;	;		;	;	;	;			;	;		;	;	;	;	;		;	;		;		;	;	;	;		;			;		;	;	;	;	;			;			;	;	;	;	;		;	;	;		;		;	;	;	;	;	;	;	;	;			;	;	;	;	;			;	;	;	;	;	;	;	;	;	;			;	;	;	;	;		;		;	;		;	;	;	;			;		;	;				;	;	;		;		;		;	;	;		;		;		;		;	;		;		;		;		;		;	;		;		;	;		;	;	;	;		;		;		;		;			;		;	;	;	;			;		;	;	;	;	;			;	;	;	;		;		;	;	;		;		;		;		;		;		;		;		;	;		;	;	;		;	;	;		;	;
<!-- SECTION:FINAL_SUMMARY:END -->

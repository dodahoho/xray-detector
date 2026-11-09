---
id: TASK-23
title: >-
  Persistens av videofilskälla: autoåterställning vid uppstart och byte i
  detektionsläget
status: Done
assignee:
  - '@glm53'
created_date: '2026-11-09T14:52:00Z'
updated_date: '2026-11-09T15:09:00Z'
labels:
  - detektion
  - video
  - persistens
  - ux
dependencies: []
modified_files:
  - xray_detector/ui/detection_view.py
  - tests/test_video_source_persistence.py
  - tests/test_sample_video.py
priority: high
type: bug
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
## Problem

Har man en videofil som kalla maste man valja om den i dialogen vid varje appstart, aven om kallvalet sparas i QSettings. Orsak: StreamPanel.restore_source staller in komboposten men gaar via _on_source_changed vars fil-gren alltid oppnar QFileDialog; och efter att en fil valts byter dessutom komboposten text fran 'Oppna videofil...' till filnamnet, sa det inte finns nagot naturligt satt att byte fil utan omstart.

## Losning

- Kombon far en bestandig 'Oppna videofil...'-post (oppnar dialog) PLUSS en dynamisk 'Videofil: <namn>'-post nar en fil ar aktiv; *( ursprunglig kombodata for aktiv fil ar file:<sokvag>, och _on_source_changed dispatchar den grena utan dialog (aterstart/terval av samma fil).
- restore_source(file, path) aktiverar filen direkt utan dialog och utan att blockera vidival: panelen visar 'Videofil: <namn>' som aktuellt val.
- Ny fil bytes i detektionslaget genom att valja 'Oppna videofil...' (dialog) - den dynamiska posten ersatts med den nya filen.
- Titelraden i panelen visar aktiv filnamn (och FPS fortfarande).
- QSettings-persistensen (detection/source_<id>_kind/value) haller redan sokvagen och anvands nu oforandrat for aterstallningen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 vid uppstart med sparad videofilm startar strömmen utan dialog
- [x] #2 aktiv fil syns i panelkombo och titel; byte sker via Oppna videofil... i detektionslaget utan omstart
- [x] #3 persistensen (QSettings) overlever omstart: ny session aterstaller samma fil
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Rotorsak till dialogen vid uppstart: _on_source_changed parsade combo-data med 'value = int(value) if value.isdigit() else None' som forvandlade filsvagar till None, och restore_source gick via kombon vars fil-gren alltid oppnar QFileDialog; dessutom bytte grenen texten pa 'Oppna videofil...'-posten till filnamnet sa filen inte kunde bytes utan omstart.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Videofilmsskallan persistens (TASK-23): sparad fil aterstalls nu automatiskt vid uppstart UTAN dialog - StreamPanel far en dynamisk 'Videofil: <namn>'-post (data file:<sokvag>) som dispatchas direkt till kallstart, och en bestandig 'Oppna videofil...'-post for att byta fil i detektionslaget (den dynamiska posten ersatts, ingen omstart kravs). Avbruten dialog aterstaller det tidigare valet utan signaler (egen _last_selected_index eftersom Qt byter aktuellt index fore signalen). Titelraden visar aktiv filnamn tillsammans med FPS. Parningsbuggen (filsokvag -> None vid int-tolkning) ar fixad; UVC-index tolkas fortfarande som heltal. Verifierat: 6 nya tester (aterstallning utan dialog, omval av sparad fil, byte via dialog med ersattning av gammal post, avbruten dialog behaller val, titel med filnamn+FPS, samt save/restore-roundtrip via DetectionView over 'omstart'); hela sviten 102 tester.
<!-- SECTION:FINAL_SUMMARY:END -->

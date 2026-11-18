---
id: TASK-135
title: >-
  Repo-hygien: runs/ och exports/ ur git, media-videor via Git LFS eller utanför
  repot
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:51:00Z'
updated_date: '2026-11-17T22:24:00Z'
labels:
  - cleanup
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - .gitignore
  - media/README.md
  - runs/detect/runs/probe/args.yaml
  - runs/detect/runs/probe/results.csv
priority: medium
type: chore
ordinal: 133000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
runs/detect/runs/probe/ (args.yaml med hårdkodad absolut sökväg + results.csv, 11 MB) är versionshanterat (utvärdering_argon.md §2.2, review_vibe_deepseek41_flash.md P3.3). Lägg runs/ och exports/ i .gitignore och kör git rm --cached. media/ innehåller 6 mp4 (38 MB) där bara 2 dokumenteras i media/README.md (P3.4): välj Git LFS eller flytta filerna utanför repot och komplettera README.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 runs/ och exports/ står i .gitignore och är borttagna från git-index
- [x] #2 Beslut för media/*.mp4 är genomfört (Git LFS eller extern lagring) och media/README.md dokumenterar alla 6 filer
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
1. Lägg runs/ och exports/ i .gitignore och ta bort dem ur git-index med git rm -r --cached, så filerna ligger kvar på disk.

2. Behåll media/*.mp4 i git enligt användarens val och komplettera media/README.md med alla sex filerna, deras längd och storlek.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
runs/ och exports/ står nu i .gitignore under projektdata-avsnittet, och runs/detect/runs/probe/args.yaml samt results.csv är borttagna ur index med git rm -r --cached. Filerna ligger kvar på disk, så en lokal ultralytics-körning fungerar som förut.

media/*.mp4 ligger kvar i git enligt användarens val (behåll och dokumentera). media/README.md dokumenterar nu alla sex filerna med simulerad ström, längd och storlek, plus vad *_faster och xray_val_30x8_* är till för. Uppmätta värden med OpenCV: alla 1280x720 @ 30 fps; slideshow 200 s, faster 75 s, val_30x8 240 s.

Verifiering: git status visar att de två runs-filerna är borttagna ur index men finns kvar i arbetskatalogen, och .gitignore innehåller runs/ och exports/. Hela sviten: 868 passed, 1 skipped, 4 failed (samma fyra Windows-specifika offscreen-fel).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
runs/ och exports/ är borta ur git-index och står i .gitignore, så ultralytics-körningar och datasetexporter inte längre hamnar i versionshanteringen; filerna ligger kvar på disk. media/*.mp4 behålls i git enligt användarens val, och media/README.md dokumenterar nu alla sex filerna med simulerad ström, längd och storlek i stället för två. Hela sviten: 868 passed, 1 skipped, inga nya fel.
<!-- SECTION:FINAL_SUMMARY:END -->

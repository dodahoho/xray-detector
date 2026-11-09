---
id: TASK-16
title: Global kraschdialog via excepthook
status: Done
assignee:
  - '@glm53'
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-09T13:57:00Z'
labels:
  - robusthet
  - gui
dependencies: []
references:
  - app
modified_files:
  - xray_detector/ui/crash_dialog.py
  - xray_detector/app.py
  - tests/test_crash_dialog.py
priority: low
type: enhancement
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
opencode-deepseek-flash har en global sys.excepthook som fångar okända undantag och visar en felruta med traceback i stället för att appen bara försvinner. Se jämförelse_qwen38.md och jämförelse_glm53.md.

Implementera i app.py: installera excepthook som visar QMessageBox med feltext och genväg till loggkatalogen; kombinera gärna med loggningsuppgiften.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ok täckta undantag i GUI-tråden visas i en felrutta istället för tyst krasch
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ny modul ui/crash_dialog.py: install_exception_dialog() ersatter sys.excepthook med en krok som (1) loggar undantaget med full traceback till xray-loggern (TASK-15:s rotationslogg), (2) skriver tracebacken till stderr for konsolkorningar, och (3) visar en kritisk QMessageBox med undantagsnamn, meddelande, informativtext och kompletta traceback som detaljtext - varefter appen far fortsatta i stallet for tyst krasch. Kraschhanteraren i sin tur är gotraderad: fel i dialoglogiken sviljs aldrig utförbart (felet är redan loggat). app.py installerar kroken direkt efter QApplication skapats. Verifierat: 3 nya tester (dialog + loggning med fake-QMessageBox inklusive Icon-mock, krok som sviljer dialogfel, install/restore av hooken); hel svit 91 tester passerar.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-147
title: Ta bort femte fliken SettingsView och använd global inställningsdialog
status: To Do
assignee: []
created_date: '2026-11-17T20:53:00Z'
labels:
  - refactor
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_hydrogen.md
priority: medium
type: enhancement
ordinal: 145000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
SettingsView finns kvar som femte flik i MainWindow bara för ThemeSection och ModelSection trots att TASK-43 flyttade vyinställningar till per-vy-dialog (utvärdering_hydrogen.md §3.5). Flytta sektionerna till en global inställningsdialog (meny/verktygsfält) och förenkla MainWindow. Görs när main_window/settings ändå rörs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 MainWindow har fyra flikar; tema- och modellinställningar nås via en global dialog
- [ ] #2 Ingen funktionalitet försvinner (manuell kontroll)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

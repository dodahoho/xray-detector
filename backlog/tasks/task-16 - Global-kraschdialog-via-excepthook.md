---
id: TASK-16
title: Global kraschdialog via excepthook
status: In Progress
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-09T13:46:00Z'
labels:
  - robusthet
  - gui
dependencies: []
references:
  - app
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
- [ ] #1 ok täckta undantag i GUI-tråden visas i en felrutta istället för tyst krasch
<!-- AC:END -->

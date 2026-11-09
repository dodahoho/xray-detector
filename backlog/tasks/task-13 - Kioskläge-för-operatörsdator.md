---
id: TASK-13
title: Kioskläge för operatörsdator
status: To Do
assignee: []
created_date: '2026-11-06T14:06:00Z'
updated_date: '2026-11-09T12:20:00Z'
labels:
  - gui
  - distribution
dependencies: []
references:
  - app
  - main-window
priority: low
type: feature
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
opencode-bigpickle och opencode-deepseek-flash har fullt kioskläge (startflagga, fullskärm utan menyer/statusrad, dold muspekare, konfigurerbart utbrytningskommando). specs.md nämner kiosk. Se jämförelse_argon.md avsnitt 5:4.

Implementera kommandoradsflagga --kiosk i app.py: startar i fullskärm, gömmer flikrad/statusrad, valfri dold pekare samt utbrytnings Shortcut (t.ex. Ctrl+Shift+Q).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 app kan startas i kioskläge (fullskärm, inga menyer, dold pekare)
- [ ] #2 kioskläget kan avslutas med konfigurerbar genväg
<!-- AC:END -->

---
id: TASK-152
title: Dela upp README.md i snabbstart + docs/ och rätta dokumentationsfel
status: In Progress
assignee: []
created_date: '2026-11-17T20:54:00Z'
updated_date: '2026-11-18T09:05:00Z'
labels:
  - docs
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
priority: low
type: docs
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
README.md är 42 kB med jättestycken under ## Lägen, dubblerad mening (rad 97), hänvisning till saknade PLAN.md (rad 3) och föråldrad beskrivning av config.classes (rad 136) (alla tre utvärderingarna). Dela upp i README.md (kom igång, krav, körning, under 150 rader), docs/arkitektur.md och docs/beteende.md; TASK-nummer och mätvärden bort ur README. Uppdatera specs.md (beskriver borttagna datasetversioner, saknar RF-DETR/syntetiska variationer) eller arkivera den i docs/historik/.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 README.md är under 150 rader med innehållsförteckning och kom-igång-avsnitt
- [ ] #2 Inga hänvisningar till filer som inte finns (PLAN.md) och ingen dubblerad mening
- [ ] #3 docs/arkitektur.md och docs/beteende.md finns; specs.md är uppdaterad eller arkiverad i docs/historik/
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

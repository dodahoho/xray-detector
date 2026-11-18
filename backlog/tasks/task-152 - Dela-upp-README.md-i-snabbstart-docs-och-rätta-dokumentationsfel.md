---
id: TASK-152
title: Dela upp README.md i snabbstart + docs/ och rätta dokumentationsfel
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-17T20:54:00Z'
updated_date: '2026-11-18T09:21:00Z'
labels:
  - docs
  - review-followup
dependencies: []
references:
  - review_lechonk_summary.md
  - utvärdering_argon.md
  - utvärdering_hydrogen.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - README.md
  - docs/arkitektur.md
  - docs/beteende.md
  - docs/historik/specs.md
  - specs.md
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

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Läs igenom README.md och för över de långa avsnitten till docs/arkitektur.md (kodstruktur, trådar, modeller, lagring) och docs/beteende.md (lägen, videokälla, inställningar, GUI-element, tangentbord, filer).
2. Skriv om README.md till en snabbstart under 150 rader med innehållsförteckning, krav, installation, körning, tester och länkar till docs/. Ta bort TASK-nummer, mätvärden och hänvisningen till PLAN.md samt den dubblerade meningen.
3. Rätta det föråldrade avsnittet om config.classes och kontrollera att alla filhänvisningar finns.
4. Uppdatera specs.md med RF-DETR och syntetiska variationer eller arkivera den i docs/historik/.
5. Kör ruff/pytest och verifiera radantal och länkar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
README.md är 95 rader med innehållsförteckning, krav, kom igång, körning, tester, utveckling och dokumentationslänkar. De långa avsnitten ligger i docs/arkitektur.md (kodstruktur, trådar, modeller, filer, CI) och docs/beteende.md (videokälla, lägen, inställningar, GUI, tangentbord). Den dubblerade meningen i Tidskrävande operationer är borta, PLAN.md-hänvisningen likaså, och specs.md ligger kvar som docs/historik/specs.md med en historiknot. Den föråldrade config.classes-beskrivningen fanns inte kvar i README; texten säger redan att klassnamnen kommer från modellen. Alla relativa länkar kontrollerade och alla fyra kvarvarande testfel är desamma som på HEAD.
<!-- SECTION:NOTES:END -->

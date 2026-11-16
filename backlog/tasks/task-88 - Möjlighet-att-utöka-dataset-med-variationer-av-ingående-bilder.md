---
id: TASK-88
title: Möjlighet att utöka dataset med variationer av ingående bilder
status: To Do
assignee: []
created_date: '2026-11-16T14:33:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 86000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
För att förbättra resultatet vid träning av detektion med ett fåtal bilder ska möjligheten finnas att aktivera bildvariationer som utökar befintligt dataset med syntetiska variationer av varje originalbild. Ex:
- rotation (0-360 grader)
- vänd (horisontellt och vertikalt)
- storlek (t ex +- 100%)
- färg (variation %)

För varje typ av bildvariation ska det om applicerbart finnas en inställning för hur många bildvariationer den typen ska generera av varje originalbild, samt hur mycket förändring som ska göras. T ex:
- Rotation 5st, 0-360grader
- Vänd horisontellt och vertikalt (här är det endast relevant med dessa val, inget antal)
- Storlek 8st, +- 50%

Dialog för att utöka dataset öppnas via knapp "Utöka med bildvariationer" där inställningar finns. Knapp Utöka genomför så att aktuellt dataset utökas. Avbryt stänger dialog utan ändring.

Det ska framgå med ikon eller liknande i dataset vy om ett bildpar är syntetiskt genererat

Det ska gå att filtrera visning så att endast originalbilder visas och/eller syntetiska bilder

Det ska gå att återställa dataset så att endast originalbilder finns kvar, dvs radera alla syntetiska bilder från dataset
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

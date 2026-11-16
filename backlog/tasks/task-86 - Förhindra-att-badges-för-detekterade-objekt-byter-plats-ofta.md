---
id: TASK-86
title: Förhindra att badges för detekterade objekt byter plats ofta
status: Done
assignee:
  - '@david'
created_date: '2026-11-16T09:49:00Z'
updated_date: '2026-11-16T09:57:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 84000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Objektklasser som detekteras i videokälla får en badge med test och sannolikhet. Den med högst sannolikhet läggs alltid överst om det är flera. Om flera objektklasser detekteras i samma bild och sannolikheten för de två klasserna ligger nära varandra kan det inträffa att de byter plats väldigt ofta vilket ger flickering och är jobbigt att titta på. Inför en tröghet i platsbyte så att det måste vara t ex 10 kontinuerliga frames för att platsbyte ska ske. Ska gå att styra trögheten i platsbyte via inställningar.
<!-- SECTION:DESCRIPTION:END -->

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
1. BadgeTracker i ui/badge.py håller en visningsordning och räknar sammanhängande ramar där en ny ordning efterfrågas; platsbytet sker först efter swap_frames ramar i följd. Nya klasser sätts in direkt på sin plats, så deras märke inte fördröjs av ett pågående platsbyte.
2. Ny inställning detection/badge_swap_frames med standard 10 ramar, läsbar via badge_swap_frames(settings) och styrbar via BadgeTracker.set_swap_frames.
3. StreamPanel läser värdet vid start och får set_badge_settings(show, hide, swap); DetectionView._on_badge_delays_changed skickar alla tre till båda panelerna.
4. BadgeSection i settings_dialog.py får fältet "Byt plats efter" med samma spara-direkt-beteende som de andra fälten.
5. Tester i tests/test_detection_badge.py: ordningen står still när sannolikheterna korsar varandra, bytet sker efter swap_frames, räknaren nollställs när ordningen går tillbaka, inställningen läses och sparas, och en ny klass får sitt märke direkt.
6. README uppdateras i avsnitten om detektionsläget och detektionsvyns inställningar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
BadgeTracker håller nu en visningsordning (self._order) i stället för att sortera om varje ram. _reorder() jämför den efterfrågade ordningen med den nuvarande: ändras bara vilka klasser som syns behålls ordningen direkt, men ändras den inbördes ordningen måste samma ordning efterfrågas swap_frames ramar i följd innan den gäller. Räknaren nollställs när ordningen går tillbaka, så en korsande sannolikhet inte ger något byte. Klasser som tillkommer sätts in direkt på sin plats (_with_new_classes), så deras märke inte väntar på ett pågående platsbyte.

Ny inställning detection/badge_swap_frames, standard 10 ramar, läses via badge_swap_frames(settings) och sätts via BadgeTracker.set_swap_frames. StreamPanel.set_badge_delays heter nu set_badge_settings(show, hide, swap) och DetectionView._on_badge_delays_changed skickar alla tre värdena till båda panelerna. BadgeSection har fått fältet "Byt plats efter" med samma spara-direkt-beteende som de andra fälten.

Verifiering: uv run pytest -q gav 617 passed, 1 skipped. Mätt i en skriptkörning med pistol 0.90/kniv 0.91 som korsar varandra varannan ram: swap_frames=1 (gamla beteendet) gav 11 platsbyten på 12 ramar, swap_frames=10 gav 0. Nya tester i tests/test_detection_badge.py täcker att ordningen står still vid korsande sannolikhet, att bytet sker efter swap_frames, att räknaren nollställs, att en ny klass får sitt märke direkt, samt att inställningen läses, sparas och slår igenom på båda panelerna.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Klassmärkena i videofönstren byter inte längre plats varje ram när två klasser ligger nära varandra i sannolikhet.

BadgeTracker håller en visningsordning i stället för att sortera om vid varje ram. En ny inbördes ordning gäller först när den efterfrågats swap_frames ramar i följd, och räknaren nollställs när ordningen går tillbaka, så en korsande sannolikhet inte ger något byte. Ändras bara vilka klasser som syns behålls ordningen direkt, och en klass som tillkommer sätts in på sin plats utan att vänta på ett pågående platsbyte.

Trögheten är inställbar: fältet "Byt plats efter" i detektionsvyns inställningar, sparat som detection/badge_swap_frames med 10 ramar som standard. Ändringen slår igenom på båda panelerna direkt.

Verifiering: hela sviten gick igenom (617 passed, 1 skipped). I en skriptkörning där pistol och kniv korsar varandra varannan ram gav swap_frames=1 (gamla beteendet) 11 platsbyten på 12 ramar, medan swap_frames=10 gav 0. Nya tester täcker stillastående ordning, bytet efter swap_frames, nollställd räknare, ny klass som får märke direkt, samt att inställningen läses, sparas och slår igenom på båda panelerna. README är uppdaterad i avsnitten om detektionsläget och detektionsvyns inställningar.

Risk: trögheten räknas i ramar, så vid en lägre bildfrekvens tar ett platsbyte proportionellt längre tid; standardvärdet 10 ramar är valt för 30 fps.
<!-- SECTION:FINAL_SUMMARY:END -->

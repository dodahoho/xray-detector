---
id: TASK-117
title: Dataset - ändring i dialogen Utöka med bildvariationer
status: Done
assignee:
  - '@david'
created_date: '2026-11-17T13:16:00Z'
updated_date: '2026-11-17T13:45:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 351000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Jag vill behålla alla tre kombinationer som nu går att välja, men med lite modifierad funktionalitet och några byten av namn/labels.

Alternativ "Alla valda variationer i varje bild" kortas ned till "Alla valda variationer"

Döp om "Syntetiska bilder per bildpar" till "Variationer per bildpar"

Flytta  som ett underval och gör det endast aktivt/valbart när "Alla valda variationer" eller "Slumpvisa kombinationer" är valda. 

Alternativet "En bild per variationstyp" kortas till "En per variationstyp" och skapar helt enkelt ett syntetiskt bildpar per aktiverad variationstyp. Därför är valet "Variationer per bildpar" inaktivt om "En bild per variationstyp" är valt.

Därtill kan vi under Storlek separera Ändring +- till separata procentuella val för öka och minska. Detta eftersom öka kan göra mer än 100% medan minska inte är applicerbart för 100% så storleken skulle bli 0.
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
1. Domän: korta etiketterna i MODES, dela scale_percent i scale_up_percent/scale_down_percent och låt total räkna en bild per aktiv typ i per_type-läget.
2. augment: variation_plan ger en bild per aktiv typ i per_type-läget, och skalningen dras mellan -scale_down_percent och +scale_up_percent.
3. Dialog: flytta antalet till ett indraget underval under Kombination som är avstängt i per_type-läget, separera Öka/Minska under Storlek och låt summeringen följa läget.
4. Tester: uppdatera befintliga och lägg till nya för undervalet, lägesbytet och den delade skalningen.
5. README: uppdatera beskrivningen av dialogen.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Etiketterna i MODES är kortade: "En per variationstyp" och "Alla valda variationer". "Slumpvisa kombinationer" är oförändrat.

per_type-läget byter innebörd: VariationSettings.total ger len(active_types) i stället för count, och variation_plan returnerar en bild per aktiv typ utan att titta på count. Store-guarden (total == 0) fungerar som förut, så en utökning i per_type-läget kräver inget antal.

Antalet är flyttat till ett indraget underval under Kombination (SUB_OPTION_INDENT = 16) och raden stängs av i per_type-läget via _update_mode, som också uppdaterar summeringen. Etiketten är "Variationer per bildpar".

Storlek har separata fält: Öka (max 300 %) och Minska (max 75 %). Gränserna räknas fram ur MIN_SCALE/MAX_SCALE i augment.py, så de följer klämningen i stället för att dupliceras. scale_percent är ersatt av scale_up_percent och scale_down_percent i VariationSettings, och _variation drar faktorn mellan -scale_down_percent och +scale_up_percent.

Summeringen följer läget: "En bild per variationstyp ger N nya bildpar från M original" respektive "N variationer per bildpar ger ...".

Verifiering: hela sviten grön (848 passed, 1 skipped). Dialogen renderad till PNG i båda lägena för att se indraget och avstängningen. ruff check är ren på de ändrade filerna; repot i övrigt har sedan tidigare 55 ruff-fel som inte rörs här.

En körning av hela sviten föll på tests/test_shortcuts.py::test_delete_key_removes_the_selected_pairs[16777223] (tangentfokus). Testet gick igenom både före och efter i omkörningar och rör ingen kod i den här uppgiften, så det är flaky sedan tidigare.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Dialogen Utöka med bildvariationer följer nu TASK-117.

Etiketterna är kortade: "En per variationstyp" och "Alla valda variationer"; "Slumpvisa kombinationer" är oförändrat.

En per variationstyp byter innebörd. Läget ger ett syntetiskt bildpar per aktiverad variationstyp i stället för att cykla över typerna count gånger. VariationSettings.total räknar därför len(active_types) i det läget, och variation_plan returnerar en bild per typ utan att läsa count. En utökning i det läget kräver alltså inget antal.

Antalet är flyttat till ett indraget underval under Kombination med etiketten "Variationer per bildpar" och är bara valbart när en bild får flera typer; i per_type-läget stängs raden av.

Storlek har separata fält, Öka (högst 300 %) och Minska (högst 75 %), i stället för Ändring ±. Gränserna räknas fram ur MIN_SCALE/MAX_SCALE i augment.py så de följer klämningen, och scale_percent är ersatt av scale_up_percent/scale_down_percent. Faktorn dras mellan -scale_down_percent och +scale_up_percent.

Summeringen följer läget, så antalet bildpar stämmer i båda fallen.

Verifiering: hela testsviten grön (848 passed, 1 skipped), ruff check ren på de ändrade filerna, och dialogen renderad till PNG i båda lägena för att bekräfta indraget och avstängningen. README är uppdaterad. Commit 75501c6.

Risker: äldre dataset med sparade variationer påverkas inte, eftersom metadata läses som förut. En tidigare utökning i per_type-läget med count > antal typer gav fler bildpar än samma val ger nu; det är avsiktligt enligt uppgiften.
<!-- SECTION:FINAL_SUMMARY:END -->

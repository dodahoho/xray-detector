---
id: TASK-88
title: Möjlighet att utöka dataset med variationer av ingående bilder
status: Done
assignee:
  - '@david'
created_date: '2026-11-16T14:33:00Z'
updated_date: '2026-11-16T14:56:00Z'
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
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. VariationSettings i domain/dataset.py: antal och styrka per variationstyp (rotation, vändning, storlek, färg) samt total.
2. infrastructure/dataset_store/augment.py: rotation, vändning, skalning och färg som funktioner på bild + annoteringar, variation_plan() som slumpar parametrarna en gång per bildpar och apply_variation() som applicerar dem på varje bild.
3. DatasetStore.add_variations() lägger till varje variation som en ny fångstgrupp med samma bildpar och metadata synthetic/source/variation; delete_synthetic() tar bort alla syntetiska bilder via delete_images().
4. DatasetService får add_variations() och delete_synthetic().
5. ui/variation_dialog.py: dialog med antal och styrka per typ, summering av antal nya bildpar samt Utöka/Avbryt.
6. Datasetvyn: knapparna "Utöka med bildvariationer" och "Återställ till original", syntetisk-märke i kortets rubrik, filter på bildtyp (alla/original/syntetiska) och utökningen i arbetstråd med upptagenindikator.
7. Tester: augmenteringens bbox-flytt, store/service, dialogen samt vyns märke, filter och återställning.
8. README: datasetläget, tangentbordet och filer och mappar.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Variationerna ligger i infrastructure/dataset_store/augment.py: variation_plan() slumpar parametrarna en gång per bildpar och apply_variation() applicerar dem på varje bild, så vänster- och högerbilden får samma rotation, vändning, storlek och färg. Rotationen vidgar bilden till den roterade rektangeln och skalningen ändrar bildens mått, så inget objekt klipps bort och annoteringen följer med objektet; färgen ändrar kontrast och ljusstyrka med cv2.convertScaleAbs. Skalningen kläms till 0,25–4,0 så en stor variation inte krymper bilden till ingenting.

DatasetStore.add_variations() lägger till varje variation som en ny fångstgrupp med originalets bilder och metadata synthetic/source/variation, och läser originalet en gång per grupp. Bara bilder utan synthetic varieras, så en ny utökning inte varierar en tidigare variation. delete_synthetic() återanvänder delete_images(), så filer, labels och num_objects städas på samma sätt som vid borttagning av bildpar.

VariationSettings i domain/dataset.py bär antal och styrka per typ samt total. Dialogen (ui/variation_dialog.py) har ett FormCard per typ, summerar antalet nya bildpar och stänger Utöka när inget är valt. Datasetvyn fick knapparna Utöka med bildvariationer (Alt+U) och Återställ till original (Alt+R), ett Syntetisk-märke i kortets rubrik med variationen som tooltip, filtret Bildtyp (alla/original/syntetiska) och utökningen i en arbetstråd med upptagenindikatorn. Osparade fångster göms när bara syntetiska bilder visas, eftersom de alltid är original.

Verifiering: uv run pytest -q gav 667 passed, 1 skipped, varav 45 nya tester i tests/test_dataset_variations.py, tests/test_variation_dialog.py och tests/test_dataset_variation_view.py samt två upptagen-tester i tests/test_busy_operations.py. ruff check på de ändrade filerna gav inga fel. Dialogen och datasetvyn renderades och granskades visuellt: märket syns bara på syntetiska kort, filtret visar rätt kort och rotationen följer objektet.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Datasetet kan utökas med syntetiska variationer av originalbilderna, och de syntetiska bildparen går att skilja från originalen, filtrera fram och ta bort igen.

Knappen Utöka med bildvariationer öppnar en dialog med antal och styrka per variationstyp: rotation (0–360°), vändning horisontellt och vertikalt, storlek (±%) och färg (±%). Dialogen räknar ut hur många nya bildpar utökningen ger innan den genomförs, och Avbryt stänger utan ändring. Varje variation blir ett eget bildpar med samma bilder som originalet, så paret hålls ihop och variationen syns som ett eget kort. Rotationen vidgar bilden och skalningen ändrar bildens mått, så inget objekt klipps bort och annoteringen följer med objektet.

I datasetvyn märks syntetiska kort med Syntetisk i rubriken och variationen som tooltip, filtret Bildtyp visar allt, bara original eller bara syntetiska, och Återställ till original raderar alla syntetiska bilder efter bekräftelse. Bara originalbilderna varieras, så en ny utökning inte varierar en tidigare variation.

Verifiering: hela sviten gick igenom (667 passed, 1 skipped) med 45 nya tester som täcker transformerna, metadata, dialogen, märket, filtret, utökningen och återställningen. Dialogen och vyn renderades och granskades visuellt.

Risk: rotation och storlek ändrar bildens mått, så datasetet får flera upplösningar. Träningens default för bildstorlek följer den vanligaste upplösningen, vilket fortfarande är originalets så länge variationerna inte dominerar.
<!-- SECTION:FINAL_SUMMARY:END -->

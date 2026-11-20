---
id: TASK-106
title: Dataset - Utöka dataset med bildvariationer
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T21:12:00Z'
updated_date: '2026-11-16T21:25:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 362000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Önskar lite ändrad funktion för att utöka med bildvariationer.

I dialogen ytöka med bildvariationer ställer man in hur många syntetiska bilder man vill skapa av varje bildpar. Därefter aktiverar man vilka typer av bildvariationer man vill göra samt inställningar för de aktiverade typerna.

Exempel: 
5st bildvariationer
Aktivera de typer som ska användas av rotation, vändning, storlek, färg
Om rotation är aktiverat går det att ställa in vinkel, annars disabled
Samma för vändning, storlek och färg.

När sedan bildvariationerna ska skapas finns en till inställning som anger om man ska: 
* skapa en bild per typ av aktiverad variation
* skapa bilder med samtliga aktiverade variationer
* skapa bilder med slumpvisa variationer (väljer bara bland de aktiverade typerna och dess inställningar)

Om slumpvida variationer är valda slumpas det bland de aktiverade funktionerna vilka som ska användas och med hur mycket (inom valt intervall)
T ex om rotation, vändning och storlek är aktiverade så kan en syntetiserad bild endast ha rotation, en annan syntetiserad bild har alla tre typerna samtidigt och en tredje bild har typerna vänding vertikalt och storleksändring.
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
1. VariationSettings i domain/dataset.py: count (antal syntetiska bilder per bildpar), mode (per_type/all/random) och en flagga per typ (rotation, scale, color; vändningen aktiveras av sina riktningar). total = count när minst en typ är aktiv.
2. augment.py: variation_plan() ger en lista av variationer per syntetisk bild enligt läget – en typ per bild (cykliskt över de aktiva typerna), alla aktiva typer, eller ett slumpvis urval av de aktiva typerna. apply_variations() applicerar listan i ordning, och describe() tar en lista (och en enstaka dict från äldre dataset).
3. store.add_variations() skriver listan i metadatafältet variation.
4. variation_dialog.py: antal bilder per bildpar och kombinationsläge i ett kort, ett checkbart FormCard per typ där fälten är avstängda när typen inte är vald, samt summering av antalet nya bildpar.
5. dataset_view: märkets tooltip visar alla variationer i bilden.
6. Tester för de tre lägena, appliceringen av flera variationer, dialogen och märket; README uppdateras.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
VariationSettings bär nu count (syntetiska bilder per bildpar), mode (per_type/all/random) och en flagga per typ; vändningen aktiveras av sina riktningar och total = count när minst en typ är aktiv. variation_plan() ger en lista av variationer per syntetisk bild: per_type tar en typ i taget cykliskt över de aktiva typerna, all lägger alla aktiva typer i varje bild, och random väljer en slumpvis delmängd (minst en typ, annars vore bilden identisk med originalet).

En bild kan nu bära flera variationer, så apply_variations() applicerar listan i ordning och metadatafältet variation sparar listan. describe() läser både listan och en enstaka variation, så äldre dataset med ett ensamt variationsobjekt fortsätter att fungera. datasetvyns märke visar alla variationer i tooltipen.

Dialogen har ett Omfattning-kort med antal och kombinationsläge, och ett checkbart FormCard per typ där Qt själv stänger av fälten när typen inte är vald. Vändningens två riktningar är förvalda men gäller bara när kortet är ikryssat.

Verifiering: hela sviten gick igenom (780 passed, 1 skipped), ruff check på de ändrade filerna gav inga fel, dialogen renderades och granskades visuellt (valda typer har aktiva fält, ovalda är gråa), och de tre lägena kördes mot ett riktigt dataset: per_type gav en typ per bild, all gav alla tre typerna i varje bild och random gav olika delmängder, med ett komplett bildpar per syntetisk bild.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Dialogen Utöka med bildvariationer ställer nu först in antalet syntetiska bilder per bildpar och sedan vilka variationstyper som ska användas. En typ är avstängd tills dess kryssruta är satt, och då är även typens fält avstängda.

Kombinationsläget avgör vad varje bild får: en typ i taget (cykliskt över de valda typerna), alla valda typer i samma bild, eller ett slumpvis urval av dem. En syntetisk bild kan därmed bära flera variationer samtidigt, och metadatafältet variation sparar listan. Äldre dataset med en enstaka variation läses fortfarande.

Verifiering: hela sviten gick igenom (780 passed, 1 skipped), ruff check på de ändrade filerna gav inga fel, dialogen renderades och granskades visuellt, och de tre lägena kördes mot ett riktigt dataset med ett komplett bildpar per syntetisk bild.

Risk: en bild med flera variationer kan få flera storleksändringar staplade om storlek är aktiv i all-läget, vilket ger större mått än en enskild variation. Skalningen kläms fortfarande till 0,25-4,0 per steg.
<!-- SECTION:FINAL_SUMMARY:END -->

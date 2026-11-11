---
id: TASK-49
title: Konsekvens i använding av GUI element
status: In Progress
assignee:
  - '@vibe'
created_date: '2026-11-11T11:58:00Z'
updated_date: '2026-11-11T15:59:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/ui/style.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/annotation_view.py
  - xray_detector/ui/dataset_view.py
  - xray_detector/ui/settings_dialog.py
  - tests/test_style.py
  - README.md
  - groma/systems/xray-detector/containers/gui-app/components/style.md
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Knappen för att starta träning i vy Träning är mycket högre än övriga knappar. Fixa och kontrollera/inför en konsekvens i GUI element hela applikationen. Kanske använda variabler för GUI element så att det blir lätt att återanvända och ändra? Också troligt att man kommer att vilja göra undantag från det och ibland ha element med egna inställningar
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Starta träning-knappen har samma höjd som övriga knappar i träningsvyn.
- [x] #2 Alla knappar i applikationen hämtar sin höjd från en gemensam modul (ui/style.py).
- [x] #3 Ett element kan få egna mått (height/width) utan att standarden ändras.
- [x] #4 Ett test verifierar att alla knappar i alla vyer har samma höjd.
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
1. Ny modul xray_detector/ui/style.py med gemensamma mått (BUTTON_HEIGHT, ICON_BUTTON_WIDTH), fabriken button() och apply_metrics(); height=None lämnar måttet till Qt så undantag per element går att göra.
2. Träningsvyn: starta/avbryt/export använder fabriken. Startknappens 40 px tas bort; huvudåtgärden markeras i stället med primary=True (fet stil) så raden blir rak.
3. Detektions-, annoterings- och datasetvyn samt inställningsknappen och dialogens Stäng-knapp använder samma mått. + och − behåller 36 px bredd via ICON_BUTTON_WIDTH.
4. Nytt test tests/test_style.py: alla knappar i alla vyer har samma höjd, träningsknapparna är lika höga, undantag och ikonknappsbredd fungerar.
5. README-avsnitt om GUI-elementen och Groma-komponent för style.py.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implementerat ui/style.py med BUTTON_HEIGHT=32, ICON_BUTTON_WIDTH=36, button() och apply_metrics(). Träningsvyns startknapp var 40 px och är nu 32 px som övriga; huvudåtgärden (Fånga bilder, Spara till dataset, Starta träning) markeras med primary=True (fet stil) i stället för en högre knapp. Detektionsvyns Försök igen (36 px), klassknapparna +/− (36 px breda), inställningsknappen och dialogens Stäng-knapp använder samma mått. Verifiering: 241 passed, 1 skipped (8 nya i tests/test_style.py); ruff rent på de nya filerna; vyerna renderade till PNG och granskade (start/avbryt lika höga, Stäng 32 px).
<!-- SECTION:NOTES:END -->

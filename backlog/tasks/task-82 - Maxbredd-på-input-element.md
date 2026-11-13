---
id: TASK-82
title: Maxbredd på input-element
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-13T14:40:00Z'
updated_date: '2026-11-13T14:56:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 80000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nu finns det vissa GUI-element av formulärtyp (textinput, select osv) som nyttjar hela tillgänliga bredden på en rad. Det ser lite konstigt ut så det kan vara bra att nyttja en maxbredd på sådana inputfält.

Gäller exempelvis vyn träning där alla inputfält för träning är väldigt breda och även knapparna för att starta och avbryta.

Även val av tema i globala inställningarna blir dropdown väldigt bred på en stor skärm.

Kanske löses bäst genom att samla sammanhängande grupper av GUI-element i ett card med lämplig label som får en maxbredd?
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Gemensam maxbredd för formulärkort finns i style.py
- [x] #2 Träningsvyns inställningar ligger i ett kort med rubrik och maxbredd; fälten och start-/avbrytknapparna blir inte bredare än kortet
- [x] #3 Temavalet i globala inställningar blir inte bredare än kortet
- [x] #4 Träningsschema, train/val-delning, sortering och modellistan har samma maxbredd
- [x] #5 Testerna passerar
<!-- AC:END -->

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
1. style.py: FORM_MAX_WIDTH, LIST_MAX_WIDTH och FormCard (QGroupBox med QFormLayout och maxbredd).
2. training_view.py: _build_settings returnerar ett FormCard "Träningsinställningar"; bildstorlekens informationsrad flyttas till en egen rad så den ryms.
3. settings_dialog.py: ThemeSection, TrainingScheduleSection, TrainValSplitSection och DatasetSortSection ärver FormCard.
4. model_settings.py: ModelSection får LIST_MAX_WIDTH, eftersom knappraden behöver mer plats.
5. settings_view.py: korten läggs till vänster så resten av bredden lämnas tom.
6. Tester i tests/test_form_width.py: maxbredd på korten, fälten och knapparna i träningsvyn samt temavalet.
7. README: dokumentera maxbredden.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
style.py har FORM_MAX_WIDTH (520), LIST_MAX_WIDTH (640) och FormCard: en QGroupBox med rubrik, ett QFormLayout i self.form och en maxbredd. ThemeSection, TrainingScheduleSection, TrainValSplitSection och DatasetSortSection ärver FormCard, så alla formulärsektioner delar mått.

TrainingView._build_settings returnerar ett FormCard 'Träningsinställningar' som läggs till vänster i vyn. Bildstorlekens upplösningslista flyttades till en egen rad och dataset- och upplösningsraderna radbryts, så de inte klipps i ett smalt kort. ModelSection har LIST_MAX_WIDTH eftersom knappraden behöver plats, och SettingsView lägger korten till vänster.

Tester: tests/test_form_width.py (10) visar fönstret i 1600x900, växlar till rätt flik och mäter faktiska bredder på kort, fält och knappar. En dold flik behåller sin standardbredd, därför växlas fliken före mätningen.

Verifiering: skärmbilder av träningsvyn och inställningsfliken i 1600x900 bekräftar att fälten, start-/avbrytknapparna, temavalet och modellistan håller sig i sina kort och att en lång datasetrad radbryts i stället för att trycka ut kortet. Hela sviten: 572 passed, 1 skipped; enda felet är test_sample_video.py::test_sample_video_meta som beror på utbytta media-filer i arbetskatalogen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Formulärfälten ligger nu i FormCard, ett kort med rubrik och en maxbredd (FORM_MAX_WIDTH 520 px), så en dropdown eller ett textfält inte längre sträcker sig över hela skärmen. Träningsvyns inställningar, temavalet, träningsschemat, train/val-delningen och sorteringen delar måttet; modellistan har en egen, något bredare maxbredd eftersom knappraden behöver plats.

Träningsvyns upplösningslista fick en egen rad och de långa datasetraderna radbryts, så informationen ryms i det smalare kortet i stället för att klippas.

Verifierat med tests/test_form_width.py, som mäter faktiska bredder i ett 1600x900-fönster, och med skärmbilder av båda vyerna. Hela sviten: 572 passed, 1 skipped; det enda felet är test_sample_video.py::test_sample_video_meta, som beror på utbytta media-filer i arbetskatalogen och faller även utan denna ändring. README beskriver måtten under GUI-element.
<!-- SECTION:FINAL_SUMMARY:END -->

---
id: TASK-175
title: Appen avslutas inte när fönstret stängs - processen hänger kvar
status: Done
assignee: []
created_date: '2026-11-20T23:03:00Z'
updated_date: '2026-11-20T23:05:00Z'
labels: []
dependencies: []
modified_files:
  - xray_detector/app.py
  - tests/test_app_shutdown.py
  - docs/arkitektur.md
type: bug
ordinal: 467000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
När appen stängs via krysset högst upp till höger försvinner fönstret men processen avslutas inte, så kommandoprompten kommer inte tillbaka i terminalen. Användaren måste trycka Ctrl+C för att komma tillbaka till skalet.

Loggen visar ingen avslutsrad: senaste raden är modelladdningen, och Ctrl+C-raden ('Avbryter: Ctrl+C') saknas i den senaste sessionen. Hängningen har funnits före TASK-173 och TASK-174 (bland annat 2026-11-20 14:38 och 20:39).

Fönstret stängs, alltså kör closeEvent klart och app.exec() returnerar. Det som återstår är Python-shutdown: Qt:s globala trådpool väntar in pågående arbete när den rivs, och CUDA/torchs statiska destructorer kan blockera när GPU:n är upptagen. Ingen av dem har en tidsgräns.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Processen avslutas när fönstret stängs, även om en bakgrundsuppgift eller CUDA håller kvar den
- [x] #2 Loggen får en avslutsrad, så en hängning går att skilja från en ren avslutning
- [x] #3 Alla tester går igenom
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
1. Logga avslutet och stäng loggarna när app.exec() returnerar.

2. Vänta in Qt:s globala trådpool med en tidsgräns i stället för att låta destructorn vänta utan gräns.

3. Avsluta processen explicit med os._exit när tidsgränsen passerats, så CUDA/torchs statiska destructorer inte kan hålla kvar den.

4. Testa båda vägarna: trådpoolen blir klar och trådpoolen hinner inte klart.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Utredning: appen avslutades rent i alla mina reproduktioner (offscreen, riktig plattform, med och utan os.execv, med och utan modell laddad, stängning under modelladdningen). Fönstret stängs, closeEvent kör klart och app.exec() returnerar inom en sekund. Det som återstår är Python-shutdown, där Qt:s globala trådpool väntar in pågående arbete och CUDA/torchs statiska destructorer kan blockera. Ingen av dem har en tidsgräns, och loggen visade ingen avslutsrad i den hängda sessionen.

Åtgärd: app.py väntar in QThreadPool.globalInstance() i högst 5 s, loggar 'Avslutar: stänger processen' och avslutar sedan processen med os._exit. closeEvent har redan synkat inställningarna, väntat in arbetstrådarna och stängt källorna, så destructorerna behövs inte. Loggarna stängs med logging.shutdown() före exit.

Verifiering: två nya tester i test_app_shutdown.py (trådpoolen blir klar respektive hänger), hela sviten 1043 passed, 1 skipped, ruff check går igenom. Kört appen med en timer som stänger fönstret: processen avslutas direkt efter app.exec() och loggen får avslutsraden.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Processen kunde bli kvar efter att fönstret stängts: closeEvent och app.exec() blev klara, men Python-shutdown väntade utan tidsgräns på Qt:s globala trådpool och på CUDA/torchs statiska destructorer. app.py väntar nu in trådpoolen i högst 5 s, loggar 'Avslutar: stänger processen' och avslutar processen med os._exit, så destructorerna inte kan hålla kvar den.

Verifierat: två nya tester (trådpoolen blir klar respektive hänger), hela sviten 1043 passed, 1 skipped, ruff check går igenom, och en körning med timer som stänger fönstret avslutas direkt med avslutsraden i loggen.

Risk: os._exit hoppar över Qt:s och CUDA:s destructorer. Inställningarna är synkade och loggarna stängda före exit, och filskrivningarna är atomiska, så inget data går förlorat.
<!-- SECTION:FINAL_SUMMARY:END -->

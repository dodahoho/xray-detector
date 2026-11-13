---
id: TASK-81
title: Hantera modeller
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-13T14:32:00Z'
updated_date: '2026-11-13T14:56:00Z'
labels: []
dependencies: []
type: feature
ordinal: 79000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Applikationen behöver ett sätt att hantera (lägga till från lokal källa, lägga till från internet, ta bort, byta visningsnamn) modeller. 
Tänker att ett bra ställe att hantera det i GUI kan vara under de globala inställningarna.
Om det finns modellrelaterade parametrar som är hårdkodade i python men passar bättre i config-fil kan det vara ett bra tillfälle att bryta ut det oxå.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Modellistan läses från models/models.json; standardlistan används när filen saknas
- [x] #2 Globala inställningar har en modellsektion som listar modellerna med visningsnamn
- [x] #3 En modell kan läggas till från en lokal viktfil och kopieras då till models/
- [x] #4 En modell kan läggas till från en http/https-adress och laddas då ner till models/
- [x] #5 En modell kan tas bort ur listan
- [x] #6 En modell kan byta visningsnamn
- [x] #7 Detektions- och träningsvyns modellväljare uppdateras när listan ändras
- [x] #8 Testerna passerar
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
1. model_registry.py: ModelCatalog som läser/skriver models/models.json; base_models() läser katalogen och faller tillbaka på standardlistan. Modellistan flyttas därmed ut ur python till config-fil.
2. Ny xray_detector/ui/model_settings.py med ModelSection: lista, Lägg till från fil, Lägg till från internet (nedladdning i bakgrundstråd), Byt namn, Ta bort.
3. SettingsView visar sektionen och sänder models_changed; MainWindow kopplar signalen till DetectionView.refresh_models() och TrainingView.refresh_models().
4. TrainingView: bryt ut modellistan till refresh_models() så väljaren kan byggas om.
5. Tester: tests/test_model_catalog.py (katalog, tillägg, borttag, namnbyte) och tests/test_model_settings.py (sektionen och uppdateringen av väljarna).
6. README: dokumentera modellhanteringen och models/models.json.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ModelCatalog i application/model_registry.py läser och skriver models/models.json med atomic_write_json. Standardlistan MODEL_SPECS används när filen saknas eller är trasig; en tom lista är ett giltigt val och faller inte tillbaka på standard.

Familjen avgörs av filändelsen (.pt -> yolo, .pth -> rfdetr). Vikterna anges relativt models_dir, så listan följer med när katalogen pekas om i config.yaml. Tillägg kopierar eller laddar ner filen till models/ med ett ledigt namn, så en befintlig vikt aldrig skrivs över, och posten får en unik nyckel ur visningsnamnet.

Borttagning rör bara listan; viktfilen ligger kvar i models/ så en modell som togs bort av misstag går att lägga till igen.

UI: ui/model_settings.py med ModelSection (lista, Lägg till från fil, Hämta från internet, Byt namn, Ta bort). Nedladdningen körs i BackgroundTask så GUI:t svarar. SettingsView sänder models_changed och MainWindow kopplar den till DetectionView.refresh_models() och den nya TrainingView.refresh_models().

Tester: tests/test_model_catalog.py (20) och tests/test_model_settings.py (10). Verifiering: hela sviten 572 passed, 1 skipped. Enda felet är test_sample_video.py::test_sample_video_meta, som faller på att media/*.mp4 i arbetskatalogen är utbytta (6000 ramar mot testets 2250) och som faller även utan denna ändring.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Modellistan ägs nu av models/models.json i stället för av en hårdkodad lista i python. ModelCatalog läser och skriver filen atomiskt och faller tillbaka på MODEL_SPECS när filen saknas eller är trasig, så en ny installation fungerar som förut.

Inställningsfliken har en ny Modeller-sektion: Lägg till från fil kopierar en .pt/.pth till models/, Hämta från internet laddar ner i en arbetstråd, Byt namn ändrar visningsnamnet utan att röra nyckeln och Ta bort tar bort posten men lämnar viktfilen kvar. En ändrad lista slår igenom direkt i både detektions- och träningsvyns modellväljare.

Verifierat med tests/test_model_catalog.py och tests/test_model_settings.py samt hela sviten (572 passed, 1 skipped). Det enda felet i sviten är test_sample_video.py::test_sample_video_meta, som beror på utbytta media-filer i arbetskatalogen och faller även utan denna ändring. README beskriver sektionen och models/models.json.
<!-- SECTION:FINAL_SUMMARY:END -->

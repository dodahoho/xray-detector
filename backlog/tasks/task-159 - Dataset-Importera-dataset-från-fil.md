---
id: TASK-159
title: Dataset - Importera dataset från fil
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-18T13:45:00Z'
updated_date: '2026-11-18T14:17:00Z'
labels: []
dependencies: []
type: feature
ordinal: 295000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Lägg till knapp "Importera" där man kan importera ett befintligt dataset i yolo format.

Det ska gå att återställa ett exporterat dataset (inklusive bildpar) genom att importera det från fil. Om funktionen att ha bildpar inte stöds när man nyttjar yolo format får du komma med en plan för hur man kan lösa det.

Kedjan: 
1) exportera dataset
2) importera dataset
Ska kunna återställa applikationens dataset precis som det var innan export

Om det vid import av dataset redan finns bilder i applikationens dataset bör man få möjlighet att ersätta befintligt, utöka befintligt eller avbryta (ingen åtgärd).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Datasetvyn har en Importera-knapp som läser ett YOLO-dataset från disk
- [x] #2 Ett exporterat YOLO-dataset kan importeras och återställer bilder, annoteringar, klasser, bildpar, fångsttid och syntetisk metadata
- [x] #3 Import till ett dataset som redan har bilder erbjuder ersätt, utöka eller avbryt
- [x] #4 Importen körs i en arbetstråd med upptagenindikator och rapporterar resultatet i statusraden
- [x] #5 Testerna täcker export-import-rundturen, ersätt/utöka och felfallen, och hela sviten är grön
- [x] #6 docs/beteende.md och docs/arkitektur.md beskriver importen och det kompletta exportformatet
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Gör YOLO-exporten komplett: kopiera images/ och labels/ till exports/yolo/ och skriv dataset.json med bild-id, fångstgrupp, fångsttid och syntetisk metadata, så exporten kan importeras tillbaka.
2. Ny modul dataset_store/import_dataset.py: import_yolo(store, data_yaml, mode) med ersätt/utöka, klassmappning, grupp-id och metadata från dataset.json när den finns; ett extern YOLO-dataset utan dataset.json får en grupp per bild.
3. Datasetvyn: Importera-knapp (Alt+M), filväljare för data.yaml, dialog med Ersätt/Utöka/Avbryt när datasetet inte är tomt, importen i BackgroundTask med indikator och statusrad.
4. Tester: rundtur export till import, ersätt/utöka, externt dataset utan dataset.json, felfall samt vy-test för knapp, dialog och statusrad.
5. Uppdatera docs/beteende.md och docs/arkitektur.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
YOLO-formatet saknar bildpar. Planen blev en sidofil: export_yolo kopierar nu images/ och labels/ till exports/yolo/ och skriver dataset.json bredvid data.yaml. Filen bär bild-id, fångstgrupp, fångsttid samt synthetic/source/variation, så importen kan återställa bildparen exakt. Ett externt YOLO-dataset utan dataset.json importeras ändå, men då blir varje bild ett eget bildpar.

Ny modul infrastructure/dataset_store/import_dataset.py: import_yolo(store, data_yaml, mode) med MODE_REPLACE och MODE_EXTEND. Ersättning tömmer datasetet först (DatasetStore.clear); utökning behåller bilderna, flyttar id och grupper med befintligt maxvärde och lägger nya klasser sist i klasslistan så att befintliga labelindex står kvar. Allt läses och valideras innan något skrivs, så ett trasigt dataset inte hinner tömma det befintliga. Bilder som inte går att läsa hoppas över och räknas i resultatet.

DatasetStore fick metadata_document(), replace_images() och clear(); yolo.py fick read_data() så data.yaml tolkas på ett ställe.

Datasetvyn: Importera-knapp (Alt+M) efter exporterna, filväljare för data.yaml som öppnas i exports/, dialog med Ersätt/Utöka/Avbryt när datasetet inte är tomt, importen i BackgroundTask med upptagenindikator och statusrad. closeEvent väntar på importen.

Tester: tests/test_dataset_import.py (11 st) täcker export-import-rundturen med variationer, externt dataset utan metadata, ersätt/utöka, split-layout, syntetisk koppling, filnamnskollision, överhoppade filer och felfallen. test_busy_operations.py täcker knappen, indikatorn, dialogen, avbrott och fel. test_export_split.py och test_shortcuts.py uppdaterade.

Dokumentation: docs/beteende.md (datasetavsnittet och genvägstabellen) och docs/arkitektur.md (exportformatet och arbetstrådslistan).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Lade till Importera i datasetvyn (Alt+M). Knappen läser ett YOLO-dataset via dess data.yaml och kör importen i en arbetstråd med upptagenindikator; statusraden rapporterar antal bilder och bildpar. Finns det redan bilder frågar dialogen Ersätt/Utöka/Avbryt, och ett tomt dataset ersätts utan fråga.

YOLO-formatet saknar bildpar. Lösningen är att export_yolo nu kopierar images/ och labels/ till exports/yolo/ och skriver dataset.json bredvid data.yaml; filen bär bild-id, fångstgrupp, fångsttid och synthetic/source/variation, så importen återställer bildparen exakt. Ett externt dataset utan dataset.json importeras ändå, men då blir varje bild ett eget bildpar. Exporten är nu en egen samling som kan flyttas mellan maskiner, vilket kostar diskplats: bilderna kopieras vid varje export, även vid träningsstart.

Importen ligger i infrastructure/dataset_store/import_dataset.py. Ersättning tömmer datasetet först; utökning behåller bilderna, flyttar id och grupper och lägger nya klasser sist så att befintliga labelindex står kvar. Allt läses och valideras innan något skrivs.

Verifiering: 970 passed, 1 skipped med pytest (seriell körning) och ruff check utan anmärkning. En manuell export-import-runda med 12 bilder i 6 par gav samma id, grupper, syntetiska kopplingar och annoteringar. Med -n auto är sviten flakig även på main (test_shortcuts och test_stream_worker), så det är inte en regression härifrån.

Uppföljning: importen läser data.yaml, inte ett zip-arkiv; vill man flytta ett dataset som en enda fil är zip nästa steg.
<!-- SECTION:FINAL_SUMMARY:END -->

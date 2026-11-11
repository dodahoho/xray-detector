---
id: TASK-50
title: >-
  Placera modellvikter under models och bästa egentränade vikter i
  models/trained
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T12:39:00Z'
updated_date: '2026-11-11T20:01:00Z'
labels: []
dependencies: []
references:
  - xray_detector/domain/config.py
  - xray_detector/application/model_registry.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/detection_view.py
  - README.md
  - xray_detector/application/app_config.py
  - xray_detector/app.py
modified_files:
  - .gitignore
  - README.md
  - xray_detector/app.py
  - xray_detector/application/app_config.py
  - xray_detector/application/model_registry.py
  - xray_detector/domain/config.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/training_view.py
  - tests/test_model_layout.py
priority: high
type: enhancement
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Applikationen sparar i dag modellvikter under datakatalogen, som default är ~/.xray-detector/models (AppConfig.models_dir). Träningen skriver till <models_dir>/v<version>/<basmodell>/weights/best.pt och modellväljaren hittar tränade modeller via <models_dir>/v*/training_manifest.json. Projektets models/-katalog är gitignorerad men används inte av applikationen; där ligger bara en kvarglömd kopia av yolo26n.pt och en tom trained/-katalog från en tidigare branch.

Önskat läge: applikationen ska spara modellvikter under projektets models/-katalog och lägga bästa vikterna för egentränade modeller i models/trained/, så att de kan väljas och användas i applikationen. models/ och models/trained/ ska vara gitignorerade och skapas vid behov.

Att ta ställning till: om models/ ska ligga relativt projektroten eller en konfigurerbar bas (appen kan startas från en annan arbetskatalog), hur basvikter (yolo26n.pt m.fl.) skiljs från egentränade vikter, hur modellväljaren märker och listar dem, och om befintliga modeller under ~/.xray-detector/models ska migreras eller bara dokumenteras. Samordna med TASK-47 som avgör snapshot per träningskörning och val av bästa checkpoint; den här uppgiften avgör den slutliga kataloglayouten.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Applikationen sparar modellvikter under projektets models/-katalog
- [x] #2 Bästa vikterna för egentränade modeller hamnar i models/trained/
- [x] #3 models/ och models/trained/ skapas vid behov och är gitignorerade
- [x] #4 Modellväljaren listar egentränade modeller från models/trained/
- [x] #5 En egentränad modell i models/trained/ kan väljas och användas för detektion
- [x] #6 Basvikter och egentränade vikter skriver inte över varandra
- [x] #7 Sökvägarna fungerar även när appen startas från en annan arbetskatalog, eller så är basen konfigurerbar
- [x] #8 Befintliga modeller under ~/.xray-detector/models hanteras, migreras eller dokumenteras
- [x] #9 README och relevant dokumentation beskriver den nya placeringen
- [x] #10 Tester täcker sökvägsuppslag och att modeller i models/trained/ hittas
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
1. AppConfig: models_dir blir ett fält med default <repo>/models (härlett ur paketets placering, oberoende av arbetskatalog) och trained_dir = models_dir/trained; ensure_dirs skapar båda. config.yaml får nyckeln models_dir (relativ sökväg tolkas mot projektroten).
2. model_registry: base_models(models_dir) ger basmodellerna med YOLO-vikterna under models/ (ultralytics laddar ner dit vid behov) medan RF-DETR behåller sina paketnamn; trained_models(trained_dir) skannar models/trained/ rekursivt efter training_manifest.json så även TASK-47:s körningskataloger hittas.
3. Träningsvyn skriver till models/trained/v<version>; detektionsvyn och träningsvyn hämtar modellistan via base_models + trained_models.
4. .gitignore: models/ och models/trained/ uttryckligen; README beskriver layouten och att ~/.xray-detector/models inte längre används.
5. Tester: sökvägsuppslag oberoende av arbetskatalog, config.yaml-override, att modeller i models/trained/ hittas och listas i väljaren, samt att bas- och egentränade vikter hålls åtskilda.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifiering:
- `uv run pytest -q`: 255 passerade, 1 skippad. Nya tests/test_model_layout.py har 13 tester.
- Manuell körning från /tmp: AppConfig().models_dir = C:\Users\Ai1\repo\xray-detector\models och trained_dir = ...\models\trained; ensure_dirs skapade båda.
- Manuell slutkontroll: en kopia av yolo26n.pt i models/trained/v1/yolo26n/weights/best.pt med training_manifest.json listades som trained-v1, och create_detector laddade YOLO från den sökvägen. Testkatalogen togs bort efteråt.
- `git check-ignore -v` bekräftar att models/ och models/trained/ ignoreras.
- Basvikterna yolo26n/s/m.pt flyttades från repo-roten till models/ (gitignorerade lokala filer), så appen slipper ladda ner dem igen.

Beslut:
- models_dir är ett fält i AppConfig (inte property) så det går att peka om i config.yaml och i tester; default räknas ur paketets placering och är därför oberoende av arbetskatalogen.
- Basvikter direkt i models/, egentränade i models/trained/ – skilda kataloger och skilda nycklar, så de kan inte skriva över varandra.
- trained_models() skannar rekursivt, så TASK-47:s snapshotkataloger (v<version>_<tidsstämpel>) hittas utan ändring här.
- RF-DETR-tränade modeller registreras fortfarande som family=yolo; det hör till TASK-48.
- Gamla ~/.xray-detector/models migreras inte automatiskt: README beskriver flytten och appen loggar en varning vid start om katalogen har innehåll.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Modellvikterna ligger nu under projektets models/ i stället för under datakatalogen. AppConfig har fått models_dir (default <repo>/models, uträknad ur paketets placering så den inte beror på arbetskatalogen) och trained_dir = models_dir/trained; båda skapas av ensure_dirs och är gitignorerade. models_dir går att peka om i config.yaml, där en relativ sökväg tolkas mot projektroten.

model_registry har delats i base_models() och trained_models(). base_models() lägger YOLO-basvikterna under models/ – ultralytics laddar ner en saknad vikt till den sökväg den får, så inget hamnar i arbetskatalogen längre – medan RF-DETR behåller sitt storleksnamn. trained_models() skannar models/trained/ rekursivt efter training_manifest.json, så varje träningskörnings katalog hittas för sig och TASK-47:s snapshotkataloger fungerar utan ändring här. Träningsvyn skriver till models/trained/v<version> och hämtar basmodellen ur specen i stället för att gissa familjen ur viktsträngen; detektionsvyn listar basmodeller följt av egentränade modeller.

Verifierat: 255 tester passerar (1 skippad), varav 13 nya i tests/test_model_layout.py som täcker sökvägsuppslag oberoende av arbetskatalog, config.yaml-override, att modeller i models/trained/ hittas och listas i väljaren, att en egentränad modell laddas för detektion, att bas- och egentränade vikter hålls åtskilda samt varningen för den gamla katalogen. En manuell slutkontroll laddade en YOLO-modell från models/trained/v1/yolo26n/weights/best.pt.

Risker och uppföljning: RF-DETR-tränade modeller registreras fortfarande som family=yolo, vilket TASK-48 äger. Gamla ~/.xray-detector/models migreras inte automatiskt; README beskriver flytten och appen loggar en varning vid start om katalogen har innehåll. Basvikterna yolo26n/s/m.pt flyttades från repo-roten till models/ (gitignorerade lokala filer).
<!-- SECTION:FINAL_SUMMARY:END -->

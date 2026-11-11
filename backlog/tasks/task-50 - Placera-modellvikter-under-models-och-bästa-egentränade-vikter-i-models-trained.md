---
id: TASK-50
title: >-
  Placera modellvikter under models och bästa egentränade vikter i
  models/trained
status: To Do
assignee: []
created_date: '2026-11-11T12:39:00Z'
labels: []
dependencies: []
references:
  - xray_detector/domain/config.py
  - xray_detector/application/model_registry.py
  - xray_detector/ui/training_view.py
  - xray_detector/ui/detection_view.py
  - README.md
priority: high
type: enhancement
ordinal: 48000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Applikationen sparar i dag modellvikter under datakatalogen, som default är ~/.xray-detector/models (AppConfig.models_dir). Träningen skriver till <models_dir>/v<version>/<basmodell>/weights/best.pt och modellväljaren hittar tränade modeller via <models_dir>/v*/training_manifest.json. Projektets models/-katalog är gitignorerad men används inte av applikationen; där ligger bara en kvarglömd kopia av yolo26n.pt och en tom trained/-katalog från en tidigare branch.

Önskat läge: applikationen ska spara modellvikter under projektets models/-katalog och lägga bästa vikterna för egentränade modeller i models/trained/, så att de kan väljas och användas i applikationen. models/ och models/trained/ ska vara gitignorerade och skapas vid behov.

Att ta ställning till: om models/ ska ligga relativt projektroten eller en konfigurerbar bas (appen kan startas från en annan arbetskatalog), hur basvikter (yolo26n.pt m.fl.) skiljs från egentränade vikter, hur modellväljaren märker och listar dem, och om befintliga modeller under ~/.xray-detector/models ska migreras eller bara dokumenteras. Samordna med TASK-47 som avgör snapshot per träningskörning och val av bästa checkpoint; den här uppgiften avgör den slutliga kataloglayouten.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Applikationen sparar modellvikter under projektets models/-katalog
- [ ] #2 Bästa vikterna för egentränade modeller hamnar i models/trained/
- [ ] #3 models/ och models/trained/ skapas vid behov och är gitignorerade
- [ ] #4 Modellväljaren listar egentränade modeller från models/trained/
- [ ] #5 En egentränad modell i models/trained/ kan väljas och användas för detektion
- [ ] #6 Basvikter och egentränade vikter skriver inte över varandra
- [ ] #7 Sökvägarna fungerar även när appen startas från en annan arbetskatalog, eller så är basen konfigurerbar
- [ ] #8 Befintliga modeller under ~/.xray-detector/models hanteras, migreras eller dokumenteras
- [ ] #9 README och relevant dokumentation beskriver den nya placeringen
- [ ] #10 Tester täcker sökvägsuppslag och att modeller i models/trained/ hittas
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

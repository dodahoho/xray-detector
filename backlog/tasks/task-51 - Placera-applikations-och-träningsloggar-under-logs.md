---
id: TASK-51
title: Placera applikations- och träningsloggar under logs
status: To Do
assignee: []
created_date: '2026-11-11T12:39:00Z'
labels: []
dependencies: []
references:
  - xray_detector/application/app_config.py
  - xray_detector/app.py
  - xray_detector/infrastructure/training/trainer.py
  - xray_detector/ui/training_view.py
  - README.md
priority: medium
type: enhancement
ordinal: 49000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Loggning sker i dag via setup_logging(config.data_dir) som skriver <data_dir>/logs/app.log med rotation (1 MB, 5 backups). Datakatalogen är som default ~/.xray-detector. Träningsprocessens stdout visas bara i träningsvyns loggruta och skrivs inte till fil, så en avslutad eller avbruten träning lämnar ingen logg efter sig. Projektets logs/-katalog är gitignorerad men används inte av applikationen; där ligger en gammal xray_20261105.log från en tidigare branch.

Önskat läge: applikationens loggar ska ligga under projektets logs/-katalog. Det gäller applikationsloggen och träningsloggen, och ska kunna omfatta fler loggtyper senare. Loggarna ska vara gitignorerade, roteras eller på annat sätt begränsas i storlek, och skrivas även när appen startas från en annan arbetskatalog.

Att ta ställning till: en fil per loggtyp (t.ex. app.log och training.log) eller en gemensam, om träningsloggen ska skrivas av träningsprocessen eller av GUI:t som fångar stdout, hur körningar skiljs åt (tidsstämpel/run-id), och om befintliga loggar under ~/.xray-detector/logs ska migreras eller bara dokumenteras. Samordna med TASK-50 så att models/ och logs/ utgår från samma bas.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Applikationsloggen skrivs under projektets logs/-katalog
- [ ] #2 Träningsloggen skrivs under logs/ och innehåller träningsprocessens utmatning
- [ ] #3 Loggarna roteras eller begränsas i storlek
- [ ] #4 Loggarna skrivs även när appen startas från en annan arbetskatalog, eller så är basen konfigurerbar
- [ ] #5 logs/ skapas vid behov och är gitignorerad
- [ ] #6 Fler loggtyper kan läggas under logs/ utan kodändring
- [ ] #7 Befintliga loggar under ~/.xray-detector/logs hanteras, migreras eller dokumenteras
- [ ] #8 README och relevant dokumentation beskriver den nya placeringen
- [ ] #9 Tester täcker loggväg och att träningsloggen skrivs
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Task description completed
- [ ] #2 Code reviewed for quality, simplicity, and maintainability
- [ ] #3 All tests pass
- [ ] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

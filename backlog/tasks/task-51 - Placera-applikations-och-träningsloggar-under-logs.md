---
id: TASK-51
title: Placera applikations- och träningsloggar under logs
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-11T12:39:00Z'
updated_date: '2026-11-11T20:16:00Z'
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
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Loggning sker i dag via setup_logging(config.data_dir) som skriver <data_dir>/logs/app.log med rotation (1 MB, 5 backups). Datakatalogen är som default ~/.xray-detector. Träningsprocessens stdout visas bara i träningsvyns loggruta och skrivs inte till fil, så en avslutad eller avbruten träning lämnar ingen logg efter sig. Projektets logs/-katalog är gitignorerad men används inte av applikationen; där ligger en gammal xray_20261105.log från en tidigare branch.

Önskat läge: applikationens loggar ska ligga under projektets logs/-katalog. Det gäller applikationsloggen och träningsloggen, och ska kunna omfatta fler loggtyper senare. Loggarna ska vara gitignorerade, roteras eller på annat sätt begränsas i storlek, och skrivas även när appen startas från en annan arbetskatalog.

Att ta ställning till: en fil per loggtyp (t.ex. app.log och training.log) eller en gemensam, om träningsloggen ska skrivas av träningsprocessen eller av GUI:t som fångar stdout, hur körningar skiljs åt (tidsstämpel/run-id), och om befintliga loggar under ~/.xray-detector/logs ska migreras eller bara dokumenteras. Samordna med TASK-50 så att models/ och logs/ utgår från samma bas.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Applikationsloggen skrivs under projektets logs/-katalog
- [x] #2 Träningsloggen skrivs under logs/ och innehåller träningsprocessens utmatning
- [x] #3 Loggarna roteras eller begränsas i storlek
- [x] #4 Loggarna skrivs även när appen startas från en annan arbetskatalog, eller så är basen konfigurerbar
- [x] #5 logs/ skapas vid behov och är gitignorerad
- [x] #6 Fler loggtyper kan läggas under logs/ utan kodändring
- [x] #7 Befintliga loggar under ~/.xray-detector/logs hanteras, migreras eller dokumenteras
- [x] #8 README och relevant dokumentation beskriver den nya placeringen
- [x] #9 Tester täcker loggväg och att träningsloggen skrivs
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
1. AppConfig får logs_dir med default <repo>/logs, härlett ur paketets placering så det inte beror på arbetskatalogen; ensure_dirs skapar katalogen och config.yaml får nyckeln logs_dir (relativ sökväg tolkas mot projektroten), samma mönster som models_dir i TASK-50.
2. app_config: log_path(logs_dir, namn) ger <logs_dir>/<namn>.log, och rotating_handler()/file_logger() delar rotationen (1 MB, 5 backups) så en ny loggtyp bara är ett nytt namn. setup_logging(logs_dir) skriver app.log och lägger bara till handlern en gång per fil.
3. Träningsvyn skriver träningsprocessens utmatning till logs/training.log via en RotatingFileHandler, med en rubrikrad per körning (tidsstämpel, datasetversion, basmodell) så körningar går att skilja åt. GUI:t äger skrivningen eftersom det redan får varje rad strömmad och loggen då finns kvar även när träningen avbryts.
4. app.py loggar till config.logs_dir i stället för datakatalogen.
5. .gitignore: logs/ finns redan och verifieras med git check-ignore; README beskriver logs/ med app.log och training.log, logs_dir i config.yaml samt att gamla ~/.xray-detector/logs inte längre skrivs.
6. Tester i tests/test_log_layout.py: sökväg oberoende av arbetskatalog, config.yaml-override, att app.log skrivs, att en ny loggtyp hamnar under logs/, och att träningsloggen får processens utmatning.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verifiering:
- `uv run pytest -q`: 266 passerade, 1 skippad (11 nya i tests/test_log_layout.py).
- Manuell körning från C:\Users\Ai1\AppData\Local\Temp: AppConfig().logs_dir = C:\Users\Ai1\repo\xray-detector\logs; setup_logging() skrev app.log där och file_logger() skrev training.log där, utan att något hamnade i arbetskatalogen.
- Manuell slutkontroll av träningsloggen: en riktig TrainingWorker (QProcess) kopplad till träningsvyn skrev rubrikraden, processens rader (epok 1/1, TRAINING_DONE) och 'Träning avslutad (kod 0)' till logs/training.log. Testkatalogen och de skapade loggfilerna togs bort efteråt.
- `git check-ignore -v logs/app.log logs/training.log` pekar på .gitignore:226 (logs/).

Beslut:
- logs_dir är ett fält i AppConfig (inte property), med default PROJECT_ROOT/logs, samma mönster som models_dir i TASK-50. Relativ logs_dir i config.yaml tolkas mot projektroten.
- En fil per loggtyp: logs/app.log och logs/training.log. log_path(logs_dir, namn) + rotating_handler() + file_logger() delar format och rotation (1 MB, 5 backups), så en ny loggtyp bara är ett nytt namn.
- Träningsloggen skrivs av GUI:t, inte av träningsprocessen: träningsvyn får redan varje rad strömmad via QProcess och kan då skriva den även när träningen avbryts, och rotationen sker i en enda process. Körningar skiljs åt av en rubrikrad med tidsstämpel, basmodell, dataset och körningskatalog.
- file_logger() sätter propagate=False så träningsraderna bara hamnar i training.log och inte dubbelt i app.log.
- Gamla ~/.xray-detector/logs migreras inte: loggar är engångsdata och en varning vid varje start skulle bli brus. README beskriver att katalogen inte längre skrivs och att filerna kan flyttas eller tas bort.
- setup_logging() tar nu logs_dir i stället för data_dir, och lägger bara till handlern om ingen handlare redan skriver till samma fil.

Modified files: README.md, xray_detector/app.py, xray_detector/application/app_config.py, xray_detector/domain/config.py, xray_detector/ui/training_view.py, tests/test_app_config.py, tests/test_log_layout.py, groma/systems/xray-detector/containers/gui-app/components/{app-config,config,training-view}.md
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Loggarna ligger nu under projektets logs/ i stället för under datakatalogen. AppConfig har fått logs_dir (default <repo>/logs, uträknad ur paketets placering så den inte beror på arbetskatalogen) och ensure_dirs skapar katalogen; logs_dir går att peka om i config.yaml, där en relativ sökväg tolkas mot projektroten. app.py startar setup_logging(config.logs_dir) och skriver logs/app.log.

app_config har delats i log_path(logs_dir, namn), rotating_handler() och file_logger(), som delar format och rotation (1 MB, 5 backups). En ny loggtyp under logs/ är därför bara ett nytt namn: log_path(logs_dir, "export") ger logs/export.log utan ny kod för katalog eller rotation. setup_logging() lägger bara till sin handler om ingen redan skriver till samma fil.

Träningsvyn skriver träningsprocessens utmatning till logs/training.log. GUI:t äger skrivningen eftersom det redan får varje rad strömmad via QProcess: loggen finns då kvar även när träningen avbryts, och rotationen sker i en enda process. Varje körning inleds med en rubrikrad med tidsstämpel, basmodell, dataset och körningskatalog, så avslutade och avbrutna körningar går att skilja åt. Loggern propagerar inte, så träningsraderna hamnar bara i training.log och inte dubbelt i app.log.

Verifierat: 266 tester passerar (1 skippad), varav 11 nya i tests/test_log_layout.py som täcker sökvägen oberoende av arbetskatalog, config.yaml-override, att app.log skrivs, att en ny loggtyp bara behöver ett namn, rotation vid 1 MB och att träningsloggen får processens utmatning. Manuellt: från en annan arbetskatalog skapades logs/app.log och logs/training.log i projektet, och en riktig QProcess-träning kopplad till träningsvyn skrev rubrikrad, processrader och slutrad till logs/training.log. git check-ignore bekräftar att logs/ är gitignorerad.

Risker och uppföljning: gamla loggar under ~/.xray-detector/logs migreras inte – README beskriver att katalogen inte längre skrivs och att filerna kan flyttas eller tas bort. Träningsloggen skrivs av GUI:t, så en kraschande app tappar de sista raderna; en orphaning av träningsprocessen loggas då inte heller.
<!-- SECTION:FINAL_SUMMARY:END -->

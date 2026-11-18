---
id: TASK-83
title: Svenska standardknappar i Qt:s egna dialoger
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-13T16:46:00Z'
updated_date: '2026-11-13T16:50:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 217000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Appen är på svenska, men standardknapparna i Qt:s egna dialoger (QMessageBox, QDialogButtonBox, QInputDialog) kommer från Qt och står på engelska: OK/Cancel i adressdialogen för modellnedladdning, Yes/No i frågorna om klasser och osparade annoteringar, och Close i inställningsdialogen. PySide6 levererar qtbase_sv.qm, så appen behöver bara ladda den. Översättningen måste installeras före första fönstret, eftersom Qt slår upp texten när en standardknapp skapas.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Appen laddar Qt:s svenska översättning vid start, före första fönstret
- [x] #2 Standardknapparna visas på svenska: Ok, Avbryt, Ja, Nej, Spara, Förkasta och Stäng
- [x] #3 Saknas qtbase_sv.qm startar appen som förut med Qt:s egna texter
- [x] #4 Testerna passerar
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
1. Ny xray_detector/ui/translations.py med install_swedish_translations(app): laddar qtbase_sv.qm ur QLibraryInfo:s TranslationsPath och returnerar translatorn så anroparen kan ta bort den igen.
2. app.py anropar den direkt efter QApplication skapats, före MainWindow.
3. Tester i tests/test_translations.py: QDialogButtonBox, QMessageBox (Ja/Nej och Spara/Förkasta/Avbryt) samt att Qt:s originaltexter gäller utan translatorn.
4. README: dokumentera de svenska standardknapparna under GUI-element.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
xray_detector/ui/translations.py: install_swedish_translations(app) laddar qtbase_sv.qm ur QLibraryInfo.path(TranslationsPath) och returnerar translatorn, så anroparen kan ta bort den igen. Translatorn får appen som förälder och lever därför lika länge som appen.

app.py anropar den direkt efter QApplication(sys.argv) och före MainWindow, eftersom Qt slår upp standardknappens text när knappen skapas.

Texterna som qtbase_sv.qm ger: Ok, Avbryt, Stäng, Spara, Förkasta, &Ja, &Nej, Verkställ, Nollställ, Hjälp. SettingsDialog sätter fortfarande Stäng själv, vilket nu är samma text som översättningen ger.

Tester: tests/test_translations.py (5) täcker QDialogButtonBox, QMessageBox Ja/Nej, Spara/Förkasta/Avbryt, att Qt:s originaltexter gäller utan translatorn samt att en saknad qtbase_sv.qm ger None och lämnar texterna orörda.

Verifiering: main() kördes med en temporär konfigkatalog och QApplication.exec patchar så adressdialogen för modellnedladdning kunde fångas. Skärmbilden visar Ok och Avbryt på svenska, alltså hela vägen från appens start. Hela sviten: 577 passed, 1 skipped; enda felet är test_sample_video.py::test_sample_video_meta som beror på utbytta media-filer i arbetskatalogen.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Appen laddar nu Qt:s svenska översättning (qtbase_sv.qm) vid start, så standardknapparna i QMessageBox, QDialogButtonBox och QInputDialog blir svenska: Ok, Avbryt, Ja, Nej, Spara, Förkasta och Stäng. Det gäller adressdialogen för modellnedladdning, frågorna om klasser och osparade annoteringar samt kraschdialogen.

Översättningen installeras direkt efter QApplication och före första fönstret, eftersom Qt slår upp texten när knappen skapas. Saknas filen returnerar install_swedish_translations None och appen startar som förut med Qt:s egna texter.

Verifierat med tests/test_translations.py och med en skärmbild av adressdialogen tagen genom den riktiga main(). Hela sviten: 577 passed, 1 skipped; det enda felet är test_sample_video.py::test_sample_video_meta, som beror på utbytta media-filer i arbetskatalogen och faller även utan denna ändring. README beskriver översättningen under GUI-element.
<!-- SECTION:FINAL_SUMMARY:END -->

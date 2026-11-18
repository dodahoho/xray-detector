---
id: TASK-112
title: Osparade bildfångster ska inte tillhöra dataset
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T10:28:00Z'
updated_date: '2026-11-17T10:38:00Z'
labels: []
dependencies: []
type: bug
ordinal: 188000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Om man i detektionsläge trycker Fånga och sedan väljer att inte spara annotering trycker man avbryt. Den osparade annoteringen behöver inte finnas kvar som en osparad bildfångst och den ska definitivt inte läggas in i dataset. Nu syns den som ett osparat bildpar i dataset.

Avbryt i Annoteringsdialog behöver aldrig behålla osparade ändringar, däremot kan man få en kontrolldialog om att det finns osparade ändringar som kommer att gå förlorade

Att växla flik från annoteringsläget kan hanteras på samma sätt som Avbryt, dvs ge kontrolldialog om det finns ändringar som inte är sparade och i annat fall bara lämna vyn utan att spara något
<!-- SECTION:DESCRIPTION:END -->

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
1. AnnotationView.discard_pending(): tar bort pending-gruppen från disk och nollställer sessionen (pending_group_id, dataset_ids, _save_requires_change, dirty-flaggor). is_saving() så en pågående sparning inte kastas under fötterna.
2. MainWindow._leave_annotation(): delas av Avbryt och flikbytet. Frågar _confirm_unsaved() när vyn är ändrad; Cancel stannar kvar, Save sparar (sparningen tar bort pending själv), annars kastas fångsten. _end_annotation_session() stänger fliken och kallar discard_pending().
3. _on_annotation_cancelled och _on_tab_changed går båda genom _leave_annotation(), så ett flikbyte beter sig som Avbryt.
4. Tester: avbryt tar bort pending, flikbyte tar bort pending, osparade ändringar ger dialog och Cancel behåller både flik och pending, Save sparar och tar bort pending. test_pending_survives_restart simulerar krasch genom att överge fönstret i stället för att avbryta.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Orsak: _on_capture skriver pending-gruppen direkt (TASK-12), men varken Avbryt eller flikbytet tog bort den. _on_annotation_cancelled stängde bara fliken, så fångsten låg kvar i pending/ och dök upp som osparat bildpar i datasetvyn.

Fix: AnnotationView.discard_pending() tar bort gruppen via dataset_service.remove_pending() och nollställer pending_group_id, dataset_ids, _save_requires_change och dirty-flaggorna. is_saving() gör att en pågående sparning inte kastas under fötterna.

MainWindow._leave_annotation() används nu av både Avbryt och _on_tab_changed: osparade ändringar ger _confirm_unsaved() (Save/Discard/Cancel), Cancel stannar kvar i vyn, Save sparar och låter sparningen ta bort pending, annars kastas fångsten via _end_annotation_session(). _on_annotation_cancelled går genom samma väg och hoppar över flikbytet när en sparning pågår, eftersom _on_annotation_saved sköter det.

En bieffekt: att öppna en osparad fångst från datasetvyn och trycka Avbryt tar också bort den. Det följer av att Avbryt aldrig behåller osparade ändringar; vill man behålla en pending-fångst låter man den ligga eller sparar den.

tests/test_pending.py::test_pending_survives_restart_and_can_be_annotated simulerade krasch genom att avbryta, vilket nu kastar fångsten. Den överger i stället fönstret utan att avbryta, vilket är en trognare kraschersättning.

Verifierat: 7 nya tester i tests/test_annotation_navigation.py (avbryt tar bort pending, flikbyte tar bort pending, Cancel behåller flik och pending, Discard kastar, Save sparar och tar bort pending, avbryt efter ett sparat par rör inte datasetet). 4 av dem faller utan fixen (kontrollerat genom att stash:a main_window.py). Hela sviten: 819 passed, 1 skipped.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Avbryt och flikbyte kastar nu den osparade fångsten i stället för att lämna den som ett osparat bildpar i datasetvyn. Pending-gruppen skrivs fortfarande vid Fånga så en krasch inte tappar bilderna, men den tas bort när annoteringen lämnas utan att sparas.

Finns osparade ändringar frågar appen först (Spara/Kasta/Avbryt): Avbryt stannar kvar i vyn, Spara sparar och tar bort pending, Kasta lämnar vyn och kastar fångsten. Utan ändringar lämnas vyn direkt utan fråga. Både Avbryt-knappen, Esc och ett flikbyte går genom samma väg, så de beter sig lika. En pågående sparning får slutföras i fred.

Att öppna en osparad fångst från datasetvyn och trycka Avbryt tar också bort den, eftersom Avbryt aldrig behåller osparade ändringar.

Verifierat med 7 nya tester i tests/test_annotation_navigation.py; 4 av dem faller utan fixen. tests/test_pending.py::test_pending_survives_restart_and_can_be_annotated simulerade krasch genom att avbryta och överger nu fönstret i stället, vilket är en trognare kraschersättning. Hela sviten: 819 passed, 1 skipped. Ruff: inga nya fynd i ändrade filer.
<!-- SECTION:FINAL_SUMMARY:END -->

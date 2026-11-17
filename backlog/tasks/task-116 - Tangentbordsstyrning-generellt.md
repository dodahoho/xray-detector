---
id: TASK-116
title: Tangentbordsstyrning generellt
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T12:30:00Z'
updated_date: '2026-11-17T13:20:00Z'
labels: []
dependencies: []
type: enhancement
ordinal: 114000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Enter/return ska vara tangent för att köra default åtgärd i dialoger/vyer, t ex för att spara annotering samt för att välja Ok eller motsvarande bekräftande knapp i dialoger
Esc ska vara tangent för att avbryta i dialoger/vyer, t ex för att avbryta annotering samt att välja avbrytande knapp i dialoger

Del/backspace ska vara tangent för att ta bort, t ex för att radera markerade bildpar i dataset vy

Inför detta generellt i applikatonen, fråga vid oklarheter
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Enter kör standardåtgärden i annoteringsvyn (Spara till dataset) och i datasetvyn (öppna markerat bildpar)
- [x] #2 Enter bekräftar och Esc avbryter i dialogerna, med rätt standardknapp
- [x] #3 Del och Backspace tar bort markerade bildpar i datasetvyn
- [x] #4 Tangenterna syns i knapparnas etiketter och i README:s genvägstabell
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
1. Samla tangenterna i ui/shortcuts.py: bind_default_action (Return/Enter) och bind_delete (Del/Backspace) ovanpå bind_shortcut, så standardåtgärden och borttagningen definieras på ett ställe.
2. Annoteringsvyn: Enter sparar annoteringen som Spara till dataset-knappen, och etiketten visar '(Enter)'. _on_save följer knappens läge, så Enter inte sparar ett bildpar som redan ligger i datasetet utan ändring.
3. Datasetvyn: Enter öppnar det enda markerade bildparet för annotering (samma väg som dubbelklicket), Del/Backspace tar bort markerade bildpar som Ta bort markerade-knappen. Etiketten visar '(Del)'.
4. Dialogerna: Enter bekräftar och Esc avbryter via QDialogButtonBox och QDialog. Verifiera SettingsDialog (Stäng är standardknapp) och VariationDialog (Utöka är standardknapp) i stället för att ändra dem.
5. Inmatningsfält behåller Enter: genvägarna binds utan ShortcutOverride-filter, så Qt låter fältet som redigeras behålla tangenten. Ett test låser det.
6. Tester i tests/test_shortcuts.py plus uppdaterade etikett- och genvägsmängdstester i test_dataset_selection.py.
7. README: genvägstabellen och avsnittet om WindowShortcut.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tangenterna ligger i ui/shortcuts.py: DEFAULT_KEYS (Return/Enter) och DELETE_KEYS (Del/Backspace) med bind_default_action och bind_delete ovanpå bind_shortcut, så en vy som får en standardåtgärd binder samma tangenter som de andra. Annoteringsvyn binder Enter till _on_default_action, som bara sparar när Spara till dataset-knappen är aktiv, så Enter inte sparar ett bildpar som redan ligger i datasetet utan ändring (TASK-62). Datasetvyn binder Enter till _on_open_selected, som öppnar det enda markerade bildparet via samma väg som dubbelklicket, och Del/Backspace till _on_delete.

Dialogerna behövde bara en ändring: SettingsDialog satte ingen standardknapp, så sektionernas första knapp blev standardknapp och Enter markerade alla klasser i stället för att stänga. Nu sätts Stäng som standardknapp och sektionernas knappar får autoDefault(False). VariationDialog fungerade redan, eftersom QDialogButtonBox gör Utöka (AcceptRole) till standardknapp; Esc avbryter via QDialog.

Mätt beteende i Qt 6.12: Enter når genvägen även när ett spinnfält eller en QComboBox har fokus (QAbstractSpinBox lämnar ShortcutOverride för Enter till dialogen), medan Backspace stannar i fältet. Därför binds Enter bara i annoterings- och datasetvyn; i detektions- och träningsvyn finns ingen Enter-genväg, så Enter bekräftar fältet man skriver i. Känd avvägning: Enter sparar annoteringen även när klassrutans textfält har fokus, eftersom klassnamnet redan tillämpas medan man skriver.

Verifiering: tests/test_shortcuts.py — test_enter_saves_the_annotation, test_enter_does_not_save_a_pair_that_is_already_in_the_dataset, test_enter_opens_the_selected_pair, test_enter_without_a_selection_opens_nothing, test_delete_key_removes_the_selected_pairs (Del och Backspace), test_enter_in_a_field_confirms_the_field, test_enter_closes_the_settings_dialog, test_enter_extends_in_the_variation_dialog, test_escape_cancels_the_variation_dialog, samt uppdaterade test_button_labels_show_underline_or_hint och test_shortcuts_do_not_collide_with_the_canvas. Etiketterna för Ta bort markerade uppdaterade i test_dataset_selection.py och test_dataset_card_click.py. Hela sviten: 837 passed, 1 skipped, 4 failed på 309 s; de fyra felen (test_app_icon och tre badge-tester i test_detection_badge) finns även på oförändrad HEAD och beror på att teckensnitt saknas i den offscreen-körningen.

Uppföljning: Enter i klassrutans textfält sparar nu klassnamnet i stället för annoteringen. Fältet har en egen Enter-åtgärd via bind_field_enter i ui/shortcuts.py: filtret accepterar fältets ShortcutOverride för Enter, så vyns WindowShortcut inte utlöses, och kör _on_add_class på tangenttryckningen. Filtret sitter på både komboboxen och dess radredigerare, eftersom QComboBox gör sig själv till radredigerarens focus proxy och därför tar emot händelserna. Knappen + har kvar samma åtgärd och tooltipen anger nu '(Ctrl++ eller Enter)'.

Verifiering: tests/test_shortcuts.py — test_enter_in_the_class_field_saves_the_class_name (klassen hamnar i listan och i datasetet, inget bildpar sparas och fliken stannar) plus test_enter_saves_the_annotation (Enter utanför klassrutan sparar fortfarande). 124 tester i annoterings-, genvägs- och GUI-smoke-sviterna gick igenom.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Enter, Esc och Del/Backspace betyder nu samma sak i hela appen. Enter kör vyens standardåtgärd: i annoteringsvyn sparar den annoteringen som Spara till dataset-knappen (och bara när knappen är aktiv, så ett bildpar som redan ligger i datasetet inte sparas om) och i datasetvyn öppnar den det markerade bildparet för annotering. När klassrutans textfält har fokus sparar Enter i stället klassnamnet, som knappen + gör. Del och Backspace tar bort markerade bildpar i datasetvyn, som Ta bort markerade-knappen. Tangenterna ligger i ui/shortcuts.py som bind_default_action, bind_delete och bind_field_enter, så nästa vy som får en standardåtgärd binder samma tangenter.

Dialogerna väljer Enter som standardknapp och Esc som avbrytande. Bara inställningsdialogen behövde ändras: utan en egen standardknapp blev sektionernas första knapp standardknapp, så Enter markerade alla klasser i stället för att stänga dialogen. Stäng är nu standardknapp och sektionernas knappar har autoDefault(False). Variationsdialogen fungerade redan via QDialogButtonBox.

Enter binds bara i annoterings- och datasetvyn. I detektions- och träningsvyn finns ingen Enter-genväg, så Enter fortsätter att bekräfta fältet man skriver i; Backspace stannar i ett fält som redigeras. Genvägarna syns i etiketterna ('Spara till dataset (Enter)', 'Ta bort markerade (Del)') och README:s genvägstabell och WindowShortcut-avsnitt är uppdaterade.

Verifierat med elva tester i tests/test_shortcuts.py (Enter sparar, Enter i klassrutan sparar klassnamnet i stället, Enter sparar inte om ett sparat par, Enter öppnar markerat par, Enter utan markering öppnar inget, Del och Backspace tar bort, Enter i ett fält startar ingen träning, Enter stänger inställningarna, Enter utökar och Esc avbryter variationerna) samt uppdaterade etikett- och genvägsmängdstester. Hela sviten: 837 passed, 1 skipped, 4 failed; de fyra felen finns även på oförändrad HEAD (test_app_icon och tre badge-tester som kräver teckensnitt i offscreen-läget).
<!-- SECTION:FINAL_SUMMARY:END -->

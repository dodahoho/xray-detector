---
type: C4 Component
title: Shortcuts
status: stable
groma:
  id: shortcuts
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/shortcuts.py
description: 'Hjälpfunktioner som ger GUI:t synliga tangentbordsgenvägar: mnemonik i etiketten eller genvägen inom parentes.'
---

mnemonic() sätter & före genvägsbokstaven så att Qt ritar den understruken och ger Alt+bokstav, medan with_hint() lägger genvägen inom parentes när etiketten saknar bokstaven, som Avbryt (Esc). bind_shortcut() binder de genvägar som inte är mnemonik (Esc, Ctrl++ och Ctrl+-) som QShortcut med WindowShortcut-kontext på vyn, så de bara är aktiva när vyn syns. Vyerna använder modulen för att hålla mnemonikbokstäverna unika per vy och skilda från flikraden, som alltid syns.

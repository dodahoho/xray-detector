---
type: C4 Component
title: Inställningsdelar och knapp per vy
status: stable
groma:
  id: settings-dialog
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/settings_dialog.py
  group: Användargränssnitt
description: Sektionerna, dialogen och knappen som öppnar en vys egna inställningar.
---

settings_button() bygger knappen Inställningar (Alt+I) med ett kugghjul framför texten. En vy utan egna inställningar får en avstängd knapp på samma plats, så placeringen är densamma oavsett flik. SettingsDialog visar vyens sektioner modalt med en Stäng-knapp; ändringarna skrivs direkt till QSettings. Vyinställningarna är träningsschemat (nattfönster och inaktivitet), datasetvyns sortering (nyast eller äldst först) och detektionsvyns klassmärke; sort_order() läser sorteringsvalet med nyast först som default. BadgeSection ställer in märkets fördröjning (visa efter, dölj efter) och trögheten i platsbyten (byt plats efter), sparade under detection/badge_show_frames, detection/badge_hide_frames och detection/badge_swap_frames, och ändringarna slår igenom på båda videofönstren utan att dialogen stängs. ThemeSection ligger här men visas i inställningsfliken, eftersom temat gäller hela appen.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | [xray_detector/ui/theme.py](../../../../../../xray_detector/ui/theme.py) | Applicerar valt tema | funktionsanrop |
| [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | [xray_detector/ui/shortcuts.py](../../../../../../xray_detector/ui/shortcuts.py) | Bygger mnemonik för knappen | funktionsanrop |
| [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | [xray_detector/ui/badge.py](../../../../../../xray_detector/ui/badge.py) | Läser och sparar märkets inställningar | direkt anrop |

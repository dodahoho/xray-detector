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

settings_button() bygger knappen Inställningar (Alt+I) med ett kugghjul framför texten. En vy utan egna inställningar får en avstängd knapp på samma plats, så placeringen är densamma oavsett flik. SettingsDialog visar vyens sektioner modalt med en Stäng-knapp; ändringarna skrivs direkt till QSettings. Träningsschemat (nattfönster och inaktivitet) är den enda vyinställningen i dag. ThemeSection ligger här men visas i inställningsfliken, eftersom temat gäller hela appen.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | [xray_detector/ui/theme.py](../../../../../../xray_detector/ui/theme.py) | Applicerar valt tema | funktionsanrop |
| [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | [xray_detector/ui/shortcuts.py](../../../../../../xray_detector/ui/shortcuts.py) | Bygger mnemonik för knappen | funktionsanrop |

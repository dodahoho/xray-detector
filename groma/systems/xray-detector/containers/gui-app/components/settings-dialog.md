---
type: C4 Component
title: Inställningar per flik
status: stable
groma:
  id: settings-dialog
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/settings_dialog.py
  group: Användargränssnitt
description: Inställningsknapp och dialog per vy, med tema och träningsschema.
---

Varje vy har en inställningsknapp (Alt+I) sist i sin åtgärdsrad som öppnar en modal dialog med de sektioner som hör till vyn. Träningsvyn visar träningsschemat (nattfönster och inaktivitet); temat ligger i sektionen Utseende, märkt som global, och finns i varje fliks dialog. Ändringarna skrivs direkt till QSettings och Stäng lämnar dem orörda.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | [xray_detector/ui/theme.py](../../../../../../xray_detector/ui/theme.py) | Applicerar valt tema | funktionsanrop |
| [xray_detector/ui/settings_dialog.py](../../../../../../xray_detector/ui/settings_dialog.py) | [xray_detector/ui/shortcuts.py](../../../../../../xray_detector/ui/shortcuts.py) | Bygger mnemonik för knappen | funktionsanrop |

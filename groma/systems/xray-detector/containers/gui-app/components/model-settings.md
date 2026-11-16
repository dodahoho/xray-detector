---
type: C4 Component
title: Modellistan
status: stable
groma:
  id: model-settings
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/model_settings.py
description: Listar modellerna och låter användaren lägga till, byta namn på och ta bort dem.
---

Sektionen i de globala inställningarna listar modellerna som väljarna i detektions- och träningsvyn bygger sina listor ur. En modell läggs till från en lokal viktfil, som kopieras till models/, eller från en http/https-adress, som laddas ner dit; adressdialogen visar ett exempel på en nedladdningslänk och kräver att adressen slutar på .pt (YOLO) eller .pth (RF-DETR). En nedladdning kan ta minuter, så tilläggen körs i en bakgrundstråd och knapparna är avstängda under tiden. Borttagningen rör bara listan: viktfilen ligger kvar i models/, så en modell som togs bort av misstag går att lägga till igen utan att laddas ner på nytt. Ändringarna skrivs direkt till models/models.json och models_changed får SettingsView att sända vidare, så väljarna i båda vyerna byggs om på en gång.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [xray_detector/ui/model_settings.py](../../../../../../xray_detector/ui/model_settings.py) | [xray_detector/application/model_registry.py](../../../../../../xray_detector/application/model_registry.py) | Läser och skriver modellistan | direkt anrop |

---
type: C4 Component
title: Svenska standardknappar
status: stable
groma:
  id: translations
  parent: gui-app
  code:
    - scanner: python
      file: xray_detector/ui/translations.py
      symbol: install_swedish_translations
description: Gör Qt:s egna standardknappar svenska genom att ladda qtbase_sv.qm.
---

Appens egna strängar är svenska, men standardknapparna i QMessageBox, QDialogButtonBox och QInputDialog kommer från Qt och står på engelska utan en översättning. install_swedish_translations() laddar qtbase_sv.qm ur PySide6:s translations-katalog och installerar den på QApplication, så Ok, Avbryt, Ja, Nej, Spara, Förkasta och Stäng blir svenska i adressdialogen för modellnedladdning, frågorna om klasser och osparade annoteringar samt kraschdialogen. Anropet sker direkt efter att QApplication skapats och före första fönstret, eftersom Qt slår upp texten när standardknappen skapas. Translatorn får appen som förälder och lever därför lika länge som den; en translator som städats bort ger engelska knappar igen. Saknas filen returneras None och appen startar som förut med Qt:s egna texter.

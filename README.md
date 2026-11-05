# X-ray detector

Applikation för detektion av objekt i två samtidiga videoströmmar, annotering av
bildpar och träning av detektionsmodeller. Se `specs.md` för krav och `PLAN.md`
för arkitektur och implementationsplan.

## Funktioner

- Detektionsläge med två kameraströmmar i split screen, overlay med klass och
  sannolikhet samt fångst av bildpar.
- Annoteringsläge med frysta bilder, befintliga detektioner inritade, flyttbara
  och storleksändringsbara boxar, klassval och nya klasser.
- Dataset i COCO-format med versionering, revisionsspårning och metadata.
- Export till COCO och YOLO med manifest (version, datum, antal bilder/objekt).
- Träningsläge för Ultralytics/YOLO med val av basmodell, dataset och parametrar.
  Detektionen pausas automatiskt under träning.
- Modellvikter sparas med metadata som kopplar dem till datasetets version.
- Fullscreen-/kioskläge (`F11`, `Esc`).

## Installation från scratch

Förutsättningar på Windows 11:

- [uv](https://docs.astral.sh/uv/) installerat. Installera med:
  `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
  Python behöver inte installeras separat – uv hämtar en passande version.
- Git, om du ska hämta koden från ett repository.
- Valfritt: NVIDIA-drivrutin med CUDA för GPU-träning och snabbare detektion.
- Två UVC-kameror inkopplade via USB 3.0.

```powershell
git clone <repository-url> xray-detector
cd xray-detector
uv sync --extra detection
```

`uv sync` skapar `.venv`, installerar projektet och utvecklingsberoendena
(pytest och PyInstaller). `--extra detection` lägger till Ultralytics och
PyTorch. Versionerna låses i `uv.lock`; kör `uv sync` igen när `pyproject.toml`
eller `uv.lock` har ändrats. Nya beroenden läggs till med `uv add <paket>`.

Vill du använda NVIDIA-GPU bör du installera rätt CUDA-byggd PyTorch enligt
instruktionerna på pytorch.org. Nedan är ett exempel – kontrollera att
CUDA-versionen matchar din drivrutin:

```powershell
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

Om du senare kör `uv sync` kan PyTorch ersättas av den låsta CPU-versionen – kör
i så fall `uv pip install`-kommandot igen.

Kontrollera sedan att PyTorch ser GPU:n:

```powershell
uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

Utan `--extra detection` startar applikationen och visar video, men detektion och
träning är avstängda. Vid första detektionen laddar Ultralytics ner standardmodellen
`yolo11n.pt` om den inte redan finns lokalt.

## Starta

Från projektroten:

```powershell
uv run xray-detector
```

eller direkt från källkoden:

```powershell
uv run python -m xray_detector
```

`uv run` ser till att miljön är synkad och kör kommandot i projektets `.venv`.
Vid första starten skapas `data/` automatiskt i den aktuella katalogen.

Användbara argument:

```text
--config PATH     Egen TOML-konfiguration
--data-dir PATH   Katalog för dataset, modeller och exporter
--verbose         Debug-loggning
```

Aktivt dataset och kamerainställningar sparas i
`%APPDATA%\xray-detector\config.toml` första gången du klickar på **Spara** i
inställningsdialogen.

## Användning

1. Kontrollera kameraenheter och modell under **Inställningar**. Standard är
   enhetsindex 0 och 1, DirectShow och `yolo11n.pt`.
2. I **Detektion** visas båda strömmarna. Klicka **Fånga bildpar** för att frysa
   bilderna och öppna annoteringen.
3. I **Annotering** ritas befintliga detektioner in automatiskt. Välj klass,
   rita nya boxar och dra i kanter/hörn för att ändra storlek. Spara lägger
   bildparet i aktivt dataset.
4. **Exportera dataset** skapar COCO- och/eller YOLO-export med manifest.
5. I **Träning** väljs basmodell, dataset och parametrar. När träningen är klar
   sparas vikterna under `data/models/<modell-id>/` tillsammans med metadata.

Tangentbord i annoteringsvyn: `Delete` tar bort vald box, mushjulet zoomar och
mittenknappen panorerar.

## Felsökning

- **Ingen video:** kontrollera kamerornas enhetsindex under **Inställningar**.
  Stäng andra program som använder kamerorna.
- **Låg bildfrekvens med två kameror:** sänk upplösning eller fps i
  inställningarna, eller anslut kamerorna till olika USB-kontroller.
- **`torch.cuda.is_available()` ger `False`:** installera CUDA-byggd PyTorch och
  kontrollera NVIDIA-drivrutinen.
- **Detektion/träning är avstängd:** kör `uv sync --extra detection` och starta
  om applikationen.

## Datastruktur

```text
data/
├─ datasets/<dataset_id>/
│  ├─ annotations.json
│  ├─ metadata.json
│  └─ images/
├─ pending/<capture_group>/      # bildpar som väntar på annotering
├─ exports/<dataset>-v<version>-<datum>/
├─ models/<model_id>/
│  ├─ best.pt
│  └─ metadata.json
└─ training/<run_id>/
```

Ett dataset får ny version vid export eller inför träning om det finns osparade
ändringar. Modellens metadata innehåller alltid `dataset_id` och
`dataset_version`.

## Tester

```powershell
uv sync --extra detection
uv run pytest
```

GUI-testerna körs headless med Qt:s offscreen-plattform och kräver ingen kamera.

Testerna täcker geometri, COCO-lagring, datasetversionering, export, pending-
bildpar, konfiguration samt datasetkonvertering och modellmetadata för träning.

## Paketering (Windows, experimentell)

En fristående build kan skapas med PyInstaller via uv:

```powershell
uv sync --extra detection
uv run pyinstaller --noconfirm --windowed --name xray-detector --paths src --collect-all ultralytics launcher.py
```

`launcher.py` finns i projektroten. Bygget är främst avsett för detektion och
annotering. Träningsläget startar en separat Python-process
(`python -m xray_detector.training.train_entry`) och kräver därför en vanlig
Python-installation med paketet installerat. Använd installationen ovan om du
behöver träna modeller.

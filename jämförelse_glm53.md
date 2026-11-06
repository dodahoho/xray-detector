# Jämförelse av alternativa implementationer — vibe-glm53

Genomgång av de övriga brancherna (`antigravity`, `opencode-bigpickle`, `opencode-deepseek-flash`, `vscode-qwen38`) ur arkitektur-, struktur-, ramverks- och funktionsperspektiv, skriven från `vibe-glm53`-implementationens synvinkel 2026-11-05.

## Översikt

| Område | antigravity | opencode-bigpickle | opencode-deepseek-flash | vscode-qwen38 | vibe-glm53 (denna) |
|---|---|---|---|---|---|
| Struktur | `src/`-paket, tydliga lager | DDD: domain/application/infrastructure | `src/`-paket, pragmatisk | platt paket | platt paket |
| Konfiguration | YAML-fil | två YAML-filer | TOML-fil | YAML + pydantic | hårdkodad dataclass + QSettings |
| Annotering | egen QWidget-canvas | saknas i GUI-del | QGraphicsScene | egen canvas | egen QWidget-canvas |
| Tester | 1 testfil | pytest-qt i dev | 8 testfiler inkl. GUI-tester | inga | tom `tests/unit` |
| ML-beroende | i basen | valfritt extra (`--extra ml`) | valfritt extra (`--extra detection`) | i basen + cu130-index | i basen (cu128-extra) |

## Vad som är bättre i de övriga brancherna, i prioritetsordning

1. **Enhetsupptäckt via pygrabber** (`opencode-bigpickle`, `infrastructure/video/device_discovery.py`) — listar riktiga kameranamn istället för hårdkodade "UVC 0/UVC 1"-poster. Störst konkret användarvinst.
2. **Testsviten** (`opencode-deepseek-flash`) — åtta testfiler (COCO, export, geometry, GUI-annotation, pending); kan porteras mot vårt dataset-API.
3. **QGraphicsScene-baserad annotering** (`opencode-deepseek-flash`, `ui/annotation_scene.py`) — kosmetiska pennor (konstant linjetjocklek oavsett zoom), inbyggd markering/flytt, halvtransparent boxfyllning. Stadigare fundament än vår handritade canvas om annoteringen ska växa.
4. **Röntgenpreprocessing** (`vscode-qwen38`, `detection/preprocess.py`) — konfigurerbar CLAHE-kontrastförbättring och inversion för röntgenbilder; domänrelevant och billig.
5. **Kameraparametrar** (`antigravity`, `video/camera_worker.py`) — `CAP_PROP_BUFFERSIZE=1` (alltid senaste bild, lägre latens) och faktisk FPS-mätning i kameratråden.
6. **Klasser/kameror/trösklar i konfigfil** (`antigravity`, `opencode-bigpickle`) i stället för hårdkodade defaults i `config.py`.
7. **Valfri ML-extra** (`opencode-bigpickle`, `opencode-deepseek-flash`) — appen startar utan torch/ultralytics installerat; bigpickle använder dessutom `opencv-python-headless` som undviker OpenCV/QT-GUI-konflikter på Windows.
8. **Atomisk JSON-skrivning** (`opencode-deepseek-flash`, `util/files.py`) — vår `dataset.json` skrivs rakt av; krasch vid sparning kan korrumpera versionens index.

## Vad som inte är värt att ta över

- **opencode-bigpickles** fulla DDD-indelning (application/domain/infrastructure) är overkill för denna kodmängd.
- **antigravitys** natt-/inaktivitetsschemaläggare för träning är en gimmick.
- **opencode-deepseek-flash** saknar Rf-DETR-stöd som finns i denna branch.

## Vad denna branch gör bättre

Temaväxling (ljust/mörkt/system) med persistens, datasetbläddring med fångstgruppering och borttagning, klasshantering i GUI, inställningspersistens (fönstergeometri, modell, källor, träningsparametrar), DSHOW-först-öppning av UVC-kameror med MSMF-fallback, FPS-pacerad videofilsuppspelning, samt tangentbordsbaserad annoteringshantering (Delete/Backspace, riktade storleksändringsmarkörer).

# X-ray detector

Applikation för detektion av objekt i röntgenvideo med annotering och träning.
Kraven finns i [docs/historik/specs.md](docs/historik/specs.md), arkitekturen i
[docs/arkitektur.md](docs/arkitektur.md) och beteendet i
[docs/beteende.md](docs/beteende.md).

## Innehåll

- [Krav](#krav)
- [Kom igång](#kom-igång)
- [Köra](#köra)
- [Tester](#tester)
- [Utveckling](#utveckling)
- [Dokumentation](#dokumentation)

## Krav

- Python 3.11 eller senare
- [uv](https://docs.astral.sh/uv/)
- Ett CUDA-rekommenderat grafikkort för detektion och träning; utan CUDA kör
  appen på CPU
- Windows 11 med två UVC-kort för den tänkta driften, men appen startar utan
  kamera och kan spela upp videofiler i stället

## Kom igång

```bash
uv sync --extra cu128
uv run python -m xray_detector.app
```

`--extra cu128` hämtar PyTorch med CUDA 12.8-stöd från PyTorch:s eget index
(krävs för GPU, inklusive RTX 50-serien/Blackwell). Utan extra installeras
CPU-bygget av PyTorch, och detektionsvyns enhetslabel visar då
`Enhet: CPU (CUDA ej tillgänglig)` i rött i stället för
`Enhet: CUDA (GPU-namn)` i grönt.

## Köra

Med RF-DETR-stöd:

```bash
uv sync --extra cu128 --extra rfdetr
```

`rfdetr` är ett valfritt extra. Saknas paketet är RF-DETR-posten avstängd i
modellväljaren och märkt `(rfdetr ej installerat)`; ett sparat RF-DETR-val
faller då tillbaka på en tillgänglig modell. Extra:t drar också in
`rfdetr[train]`, eftersom RF-DETR-träningen annars stannar på ett ImportError
innan första epoken.

`pygrabber` installeras automatiskt på Windows och ger videokällorna deras
riktiga DirectShow-namn. Utan den visas bara index (`UVC 0`, `UVC 1`), vilket
gör det svårt att skilja ett capture-kort från en virtuell kamera.

## Tester

```bash
uv run pytest -q -n auto
uv run ruff check .
```

`-n auto` fördelar filerna över alla kärnor med
[pytest-xdist](https://pytest-xdist.readthedocs.io/). Markören `slow` är
registrerad i `pyproject.toml` för tester som startar `MainWindow`, så
`uv run pytest -m "not slow"` kör sviten utan dem. CI kör samma kommandon på
GitHub Actions; detaljerna finns i [docs/arkitektur.md](docs/arkitektur.md).

## Utveckling

Uppgifterna hanteras i [Backlog.md](https://github.com/MrLesk/Backlog.md) och
arkitekturen följs upp i [Groma.md](https://github.com/MrLesk/Groma.md).
Konfigurationen för båda ligger i repot, och kommandoverktygen installeras med
npm:

```bash
backlog browser
groma web
```

Kodkvaliteten kontrolleras med [ruff](https://docs.astral.sh/ruff/),
konfigurerad i `pyproject.toml` under `[tool.ruff]`. Grinden är `ruff check`
och ska gå igenom innan en ändring committas:

```bash
uv run ruff check .
uv run ruff check --fix .
```

## Dokumentation

- [docs/arkitektur.md](docs/arkitektur.md) – lager, trådar, modeller, filer och CI
- [docs/beteende.md](docs/beteende.md) – lägen, videokälla, inställningar, GUI och tangentbord
- [docs/rapporter/bildvariationer.md](docs/rapporter/bildvariationer.md) – utvärdering av syntetiska bildvariationer vid ett tiotal bildpar
- [docs/historik/specs.md](docs/historik/specs.md) – den ursprungliga kravspecifikationen

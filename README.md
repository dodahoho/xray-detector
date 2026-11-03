# X-ray Detector

Applikation för detektion av objekt i video med röntgenbilder från två UVC USB 3.0 videoströmmar i Windows 11, med inbyggt **Detektionsläge**, **Annoteringsläge** och **Träningsläge**.

## Funktioner
* **Detektionsläge (Default):**
  * Kör varje inkommande videoström genom vald detektionsmodell (**YOLO26**, **YOLO11**, **RF-DETR** eller egentränad modell) i en dedikerad bakgrundstråd.
  * Visar de två strömmarna i **split-screen** med rektanglar, klassnamn och sannolikhet (%).
  * **Fånga-knapp** (eller `Space`) som fryser aktuella bildrutor samt befintliga detektioner från båda strömmarna och öppnar **Annoteringsläget**.
* **Annoteringsläge:**
  * Visar de två frysta bilderna sida vid sida med alla detektioner från fångsttillfället automatiskt inritade.
  * Samtliga rektanglar kan **storleksändras genom att trycka och dra i ett hörn eller en kant**, flyttas eller tas bort. Nya rektanglar ritas genom att klicka och dra på bilden.
  * Ändra klass genom att välja från klasslistan eller skriva in en helt ny klass (`+ Ny klass`).
  * **Spara** fyller på det interna COCO-datasetet och återgår direkt till Detektionsläget.
  * Exportera versionshanterade dataset (`v1`, `v2`, ...) till **COCO**, **YOLO** eller **COCO+YOLO** där **versionssiffra, datum och antal bildobjekt** tydligt framgår.
* **Träningsläge:**
  * Välj basmodell (t.ex. YOLO26, RF-DETR), dataset-version och träningsparametrar.
  * Kan startas direkt, schemaläggas till **nattetid** eller köras automatiskt vid **inaktivitet**.
  * Kan automatiskt **pausa detektionen under träning** för att maximera tillgängliga hårdvaruresurser.
  * Sparar färdigtränade modellvikter med **samma versionssiffra som det dataset som använts**.
* **Fullskärm / Kioskläge:** Växla när som helst med `F11` eller knappen i toppmenyn (kan även aktiveras vid start via `kiosk_fullscreen: true` i `config.yaml`).

## Kör applikationen (med `uv`)

```powershell
# Installera/synka beroenden
uv sync

# Starta applikationen
uv run python main.py
```

## Kör tester

```powershell
uv run pytest -v
```

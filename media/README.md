# media/

Demovideor som simulerar de två röntgenströmmarna när fysiska UVC-kort
saknas.

| Fil | Simulerar |
|---|---|
| `xray_slideshow_side.mp4` | Ström 1 (sidovy) |
| `xray_slideshow_top.mp4` | Ström 2 (toppvy) |

Båda är 1280x720 @ 30 fps, 200 sekunder (6000 ramar).

## Köra appen utan UVC-kort

Välj "Öppna videofil..." i respektive strömpanel och peka ut filerna här,
eller återställ senaste källval i inställningarna (källvalet persistas).
Filväljaren öppnas i den här katalogen första gången; pekar du ut en fil
någon annanstans kommer nästa filväljare ihåg den katalogen.

## Tester

`tests/test_sample_video.py` kör riktig videogejd (FileSource, FPS-pacing,
looping och StreamWorker) mot dessa filer och **skippas automatiskt på
maskiner där filerna saknas**, så testsviten fungerar även i rent CI.
De syntetiska videorna i `tests/test_stream_worker.py` (genereras med
OpenCV) används fortfarande för grundtesterna och kräver inga binärer.

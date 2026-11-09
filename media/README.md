# media/

Demovideor som simulerar de två röntgenströmmarna när fysiska UVC-kort
saknas.

| Fil | Simulerar |
|---|---|
| `xray_slideshow_side.mp4` | Ström 1 (sidovy) |
| `xray_slideshow_top.mp4` | Ström 2 (toppvy) |

Båda är 1280x720 @ 30 fps, 75 sekunder.

## Köra appen utan UVC-kort

Välj "Öppna videofil..." i respektive strömpanel och peka ut filerna här,
eller återställ senaste källval i inställningarna (källvalet persistas).

## Tester

`tests/test_sample_video.py` kör riktig videogejd (FileSource, FPS-pacing,
looping och StreamWorker) mot dessa filer och **skippas automatiskt på
maskiner där filerna saknas**, så testsviten fungerar även i rent CI.
De syntetiska videorna i `tests/test_stream_worker.py` (genereras med
OpenCV) används fortfarande för grundtesterna och kräver inga binärer.

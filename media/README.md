# media/

Demovideor som simulerar de två röntgenströmmarna när fysiska UVC-kort
saknas. Alla är 1280x720 @ 30 fps och spårade i git, så en klon räcker för
att köra appen och de tester som använder riktig videogejd.

| Fil | Simulerar | Längd | Storlek |
|---|---|---|---|
| `xray_slideshow_side.mp4` | Ström 1 (sidovy) | 200 s (6000 ramar) | 5,8 MB |
| `xray_slideshow_top.mp4` | Ström 2 (toppvy) | 200 s (6000 ramar) | 10,1 MB |
| `xray_slideshow_side_faster.mp4` | Ström 1 (sidovy), snabbare klippning | 75 s (2250 ramar) | 2,9 MB |
| `xray_slideshow_top_faster.mp4` | Ström 2 (toppvy), snabbare klippning | 75 s (2250 ramar) | 4,0 MB |
| `xray_val_30x8_side.mp4` | Ström 1 (sidovy), 30x8-sekvens för validering | 240 s (7200 ramar) | 6,7 MB |
| `xray_val_30x8_top.mp4` | Ström 2 (toppvy), 30x8-sekvens för validering | 240 s (7200 ramar) | 9,9 MB |
| `xray_val2_30x8_side.mp4` | Ström 1 (sidovy), 30x8-sekvens v2 för validering | 240 s (7200 ramar) | 6,9 MB |
| `xray_val2_30x8_top.mp4` | Ström 2 (toppvy), 30x8-sekvens v2 för validering | 240 s (7200 ramar) | 10,6 MB |

`*_faster` är samma innehåll som originalslideshowen men klippt snabbare, så
en demokörning hinner igenom fler scener. `xray_val*_30x8_*` är längre
sekvenser avsedda för att validera detektion och spårning över tid.

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

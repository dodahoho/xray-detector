---
id: doc-1
title: 'Beslut: opencv-python-headless'
type: specification
created_date: '2026-11-18T09:12:00Z'
updated_date: '2026-11-18T09:12:00Z'
---
## Frågan

Ska den direkta dependencyn `opencv-python` bytas mot `opencv-python-headless`?
Förslaget kom från `utvärdering_argon.md` och `utvärdering_hydrogen.md`: appen
ritar allt i Qt och öppnar inga OpenCV-fönster, så GUI-delen av OpenCV behövs
inte.

## Vad som kontrollerades

1. **Inga GUI-anrop i koden.** Sökning efter `cv2.imshow`, `cv2.namedWindow`,
   `cv2.waitKey` och `cv2.destroyAllWindows` ger inga träffar. Koden använder
   bara `imread`, `imwrite`, `VideoCapture` och `VideoWriter`.
2. **Kamerastöd på Windows.** Den installerade byggnaden är
   `opencv-python-headless 5.0.0.93` (`GUI: NONE`). `cv2.getBuildInformation()`
   rapporterar `DirectShow: YES` och `FFMPEG: YES (prebuilt binaries)`, och
   `cv2.VideoCapture(0, cv2.CAP_DSHOW)` öppnade en riktig kamera och läste en
   ram (640x480) i den här miljön. Headless-hjulets videoio innehåller alltså
   både DirectShow och MSMF; det är bara highgui som saknas.
3. **Vem drar in GUI-byggnaden?** `ultralytics` deklarerar `opencv-python`,
   medan `rfdetr` drar in `roboflow`, som deklarerar
   `opencv-python-headless`. Båda hjulen ligger redan i `uv.lock` och i venv,
   och båda installerar samma `cv2`-paket.

## Beslut

Den direkta dependencyn är kvar som `opencv-python`. Ett byte till
`opencv-python-headless` skulle inte ta bort GUI-hjulet, eftersom `ultralytics`
kräver det, och då skulle två hjul som äger samma `cv2`-katalog installeras i
samma miljö. Vilken byggnad som vinner beror då på installationsordningen,
vilket är svårare att felsöka än att behålla ett hjul som redan fungerar.

Kamerastödet är verifierat, så bytet är säkert den dag `ultralytics` slutar
kräva `opencv-python`. Tills dess vinner inget på bytet: appen importerar
aldrig highgui, och den GUI-del som följer med används inte.

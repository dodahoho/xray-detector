---
id: TASK-39
title: Växling UVC0 och UVC1
status: Done
assignee: []
created_date: '2026-11-11T10:04:00Z'
updated_date: '2026-11-11T10:27:00Z'
labels: []
dependencies: []
modified_files:
  - pyproject.toml
  - uv.lock
  - xray_detector/domain/capture.py
  - xray_detector/infrastructure/video/devices.py
  - xray_detector/infrastructure/video/source.py
  - xray_detector/application/video_service.py
  - xray_detector/ui/video_settings.py
  - xray_detector/ui/settings_view.py
  - xray_detector/ui/detection_view.py
  - xray_detector/ui/main_window.py
  - tests/test_video_source_persistence.py
  - tests/test_video_modes.py
  - README.md
  - groma/systems/xray-detector/containers/gui-app/components/video-settings.md
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
1. Med endast ett fysiskt UVC-kort kopplat till datorn kan jag få samma bild från UVC0 och UVC1. Det är lägre frame rate på UVC0 (omkring 8 fps) än på UVC1 (närmare 30 fps). Förklara!
2. När jag växlar mellan UVC0 och UVC1 får jag ett fel i loggen: "E2026-11-11 10:57:07.511581 (  504)  [ERR] [VCAMDS] Failed to open NBX hive". Beror det på något fel i koden?
3. Loggar upprepar sig vid byte av kort. Kontrollera om det är normalt. Exempel på output:
I2026-11-11 10:57:07.539938 (  504) [INFO] [VCAMDS] Requested to perform initializing sequence
I2026-11-11 10:57:07.539938 (  504) [INFO] [VCAMDS] Already initialized
I2026-11-11 10:57:07.539938 (  504) [INFO] [VCAMDS] Requested to perform initializing sequence
I2026-11-11 10:57:07.539938 (  504) [INFO] [VCAMDS] Already initialized
I2026-11-11 10:57:07.625067 (  504) [INFO] [VCAMDS] Requested to perform initializing sequence
I2026-11-11 10:57:07.625067 (  504) [INFO] [VCAMDS] Already initialized
I2026-11-11 10:57:07.625067 (  504) [INFO] [VCAMDS] Requested to perform initializing sequence
I2026-11-11 10:57:07.625067 (  504) [INFO] [VCAMDS] Already initialized
I2026-11-11 10:57:07.625067 (  504) [INFO] [VCAMDS] Requested to perform initializing sequence
I2026-11-11 10:57:07.625067 (  504) [INFO] [VCAMDS] Already initialized
I2026-11-11 10:57:07.625067 (  504) [INFO] [VCAMDS] Requested to perform initializing sequence
I2026-11-11 10:57:07.625067 (  504) [INFO] [VCAMDS] Already initialized
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Enhetsväljaren visar enheternas riktiga namn i stället för "UVC n" när pygrabber finns
- [x] #2 Inställningarna erbjuder de upplösningar och format som den valda enheten rapporterar
- [x] #3 Vald upplösning och format används när en UVC-källa öppnas
- [x] #4 Valet sparas mellan starter
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. pyproject.toml: pygrabber blir ett riktigt Windows-beroende (sys_platform == 'win32') i stället för ett valfritt extra, så enhetsnamnen alltid finns. Uppdatera uv.lock.
2. domain/capture.py: ny VideoMode(width, height, fourcc) som beskriver en vald inspelningsmodalitet.
3. infrastructure/video/devices.py: list_device_modes(index) som läser enhetens faktiska kapabiliteter via DirectShow (pygrabber VideoInput.get_formats), avdubblade på (bredd, höjd, format).
4. infrastructure/video/source.py: UvcSource tar emot en VideoMode och skickar FOURCC + upplösning i params-listan vid öppning. Det är enda sättet som fungerar med DSHOW-backend; cap.set(CAP_PROP_FOURCC) efter öppning ignoreras.
5. application/video_service.py: set_source vidarebefordrar modaliteten.
6. ui/settings_view.py: ny grupp "Videokälla" med enhet, upplösning och format. Listorna fylls från den valda enhetens kapabiliteter och valet sparas i QSettings.
7. ui/detection_view.py: läser sparat val och skickar det när en UVC-källa öppnas.
8. Tester för kapabilitetslistning, params-vid-öppning, inställningsvyns listor och att detektionsvyn skickar vald modalitet.
9. README: enhetsnamn, videogruppen och rekommendationen MJPG 1920x1080 för MS2109-kortet.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Utredning på användarens maskin (2026-11-11). Mätningarna är gjorda med appens egen kodväg (cv2.VideoCapture med CAP_DSHOW) och med PnP-enumering.

## 1. Samma bild från UVC0 och UVC1, och varför 8 mot 30 fps

Maskinen har exakt en fysisk capture-enhet: en MacroSilicon MS2109 USB 2.0 HDMI-dongle ("USB Video", USB\VID_345F&PID_2109). Utöver den finns NVIDIA Broadcast installerad som virtuell kamera (ROOT\UNNAMED_DEVICE\0000, DirectShow-namn "Camera (NVIDIA Broadcast)").

Index 0 är det fysiska kortet, index 1 är NVIDIA Broadcasts virtuella kamera. Samma bild syns för att Broadcast är satt att fånga samma kort och publicera det igen. Att appen kallar båda "UVC <index>" beror på att list_devices() faller tillbaka på två hårdkodade index 0 och 1 när pygrabber saknas — och pygrabber är ett valfritt extra (windows) som inte är installerat och som README:s körinstruktion inte nämner. Etiketten säger alltså inget om vad enheten är.

Frame rate-skillnaden är pixelformatet. Kortet förhandlar YUY2 i 1920x1080, vilket på USB 2.0 kapas av bandbredden. Uppmätt på index 0: 1080p YUY2 9,3 fps, 720p YUY2 21,7 fps, 480p YUY2 52,9 fps — alla kring 35-40 MB/s, alltså USB 2.0-taket. Den virtuella kameran annonserar 1920x1080@30 i loggen ("Querying stream output successful. Params: 1920x1080@30/1") och levererar sin egen förskalade ström, så den är inte bunden av kortets USB-bandbredd.

Kortet stöder MJPG, som ryms i samma länk. Appen begär aldrig MJPG. Dessutom ignoreras cap.set(CAP_PROP_FOURCC, ...) efter öppning av DSHOW-backend; formatet måste skickas i params-listan till VideoCapture. Uppmätt: MJPG 1080p 52 fps på signalöst ingång (chippen free-runner på en statisk svart bild; med levande signal är 30 fps chippens 1080p-läge). YUY2 1080p gav 9,3 fps i samma test.

## 2. "Failed to open NBX hive"

Inte ett fel i koden. Raden skrivs av NVIDIA Broadcasts DirectShow-filter (VCAMDS = virtual camera DirectShow, NBX = Broadcasts registerhive) när filtret initieras. Uppmätt: att enbart öppna index 0 gav 0 VCAMDS-rader och 0 fel; att enbart öppna index 1 gav 73 VCAMDS-rader och exakt 1 "Failed to open NBX hive". Meddelandet kommer före första ramen och påverkas inte av hur vi stänger enheten.

Det betyder också att slutsatsen i TASK-28 var fel: trådaffinitetsfixen tog bort appens andel av problemet, men kunde aldrig ta bort den här raden, eftersom den kommer från drivrutinens initiering.

## 3. Upprepade loggrader

Normalt. En enda öppning av index 1 gav 19 "Requested to perform initializing sequence" och 18 "Already initialized". Det är filtrets egen initieringshandskakning som upprepas en gång per intern initiering. Det är drivrutinens loggning, inte appens, och går inte att tysta från appen.

## Möjliga åtgärder i koden

- Enhetsnamn: gör pygrabber till ett riktigt Windows-beroende (eller dokumentera --extra windows i README), så väljaren visar "USB Video" och "Camera (NVIDIA Broadcast)" i stället för "UVC 0"/"UVC 1".
- Frame rate: begär MJPG i params-listan när UvcSource öppnar, så kortet ger 30 fps i stället för 9.

## Åtgärder

Enhetsnamn: pygrabber är nu ett riktigt Windows-beroende (sys_platform == 'win32') i stället för ett valfritt extra, så namnen finns utan extra steg. Källväljaren visar "UVC 0 · USB Video" och "UVC 1 · Camera (NVIDIA Broadcast)" i stället för två identiska "UVC n".

Upplösning och format: ny grupp "Videokälla" i inställningsfliken med enhet, upplösning och format. Listorna fylls från enhetens egna DirectShow-kapabiliteter via pygrabber (IAMStreamConfig), så bara lägen enheten faktiskt erbjuder går att välja: 22 för MS2109-kortet, 33 för den virtuella kameran. Valet sparas i QSettings (video/width, video/height, video/fourcc) och används när en UVC-källa öppnas. "Auto" lämnar tillbaka till drivrutinen.

Formatet skickas i params-listan till VideoCapture vid öppning. Det är enda vägen: cap.set(CAP_PROP_FOURCC) efter öppning ignoreras av DSHOW-backend, vilket var därför den tidigare koden alltid fick YUY2.

Kapabilitetslistningen sker först när inställningsfliken visas (showEvent), inte vid appstart: DirectShow-enumereringen instansierar enhetsfiltren, och för den virtuella kameran skriver drivrutinen då en rad VCAMDS-loggrader.

## Verifiering

Uppmätt genom UvcSource mot det fysiska kortet: Auto (ingen modalitet) 1920x1080 YUY2 9,3 fps; MJPG 1920x1080 52,9 fps; MJPG 1280x720 52,1 fps; YUY2 1920x1080 9,3 fps. Alltså samma siffror som i utredningen, nu styrbara.

14 nya tester i tests/test_video_modes.py: avdubblering och ordning i list_device_modes, params-vid-öppning (inkl. att RGB24 utan fyra tecken hoppar över FOURCC), att VideoService vidarebefordrar modaliteten, QSettings-rundtur, inställningsvyns listor och sparande, samt att detektionsvyn skickar sparat val. Hela sviten 178 passed, 1 skipped, tre körningar i rad. uv lock --check är ren. Ruff: inga nya anmärkningar utöver de mönster som redan finns i filerna (blind except i devices.py följer befintlig stil).

UI verifierat genom att rendera inställningsfliken och detektionsvyn: enhetsnamnen syns i båda, upplösningslistan har 12 poster för kortet och formatlistan MJPG/YUY2.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Utredningen visar att "UVC 0" och "UVC 1" inte var två kort: index 0 är en MacroSilicon MS2109 USB 2.0 HDMI-dongle och index 1 är NVIDIA Broadcasts virtuella kamera. Samma bild syntes för att Broadcast fångar samma kort. Fps-skillnaden var pixelformatet — kortet förhandlade okomprimerad YUY2, som på USB 2.0 kapas till 9,3 fps i 1080p mot 52,9 fps med MJPG. "Failed to open NBX hive" och de upprepade initieringsraderna skrivs av NVIDIA Broadcasts DirectShow-filter när den virtuella kameran öppnas (0 rader för index 0, 73 rader och 1 fel för index 1) och går inte att påverka från appen. Slutsatsen i TASK-28 var alltså fel på den punkten.

Åtgärder: pygrabber är nu ett riktigt Windows-beroende, så källväljaren visar enheternas namn. Inställningsfliken har en ny grupp Videokälla där enhet, upplösning och format väljs ur enhetens egna DirectShow-kapabiliteter (22 lägen för kortet, 33 för den virtuella kameran). Valet sparas och används när en UVC-källa öppnas, och formatet skickas i params-listan vid öppning eftersom cap.set(CAP_PROP_FOURCC) ignoreras av DSHOW-backend. Listningen sker först när fliken visas, så appstarten inte drar igång den virtuella kamerans loggning.

Verifierat: 14 nya tester, hela sviten 178 passed, 1 skipped, stabilt över tre körningar. Uppmätt genom UvcSource: Auto 9,3 fps, MJPG 1080p 52,9 fps, MJPG 720p 52,1 fps. UI renderat och kontrollerat i både inställnings- och detektionsvyn.
<!-- SECTION:FINAL_SUMMARY:END -->

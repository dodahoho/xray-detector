---
type: C4 System
title: X-ray detector
status: stable
groma:
  id: xray-detector
description: Skrivbordsapplikation för detektion av objekt i röntgenvideo, annotering av fångade bilder och träning av detektionsmodeller.
---

Operatören bevakar två parallella röntgenströmmar (UVC-kameror eller videofiler) med objektsdetektion i realtid, fångar bildpar, annoterar dem med rektanglar och klasser, lagrar dem i ett YOLO-dataset och tränar YOLO26/RF-DETR-modeller på resultatet. Består av en PySide6-GUI-process och en separat träningsprocess som GUI:t startar som subprocess.

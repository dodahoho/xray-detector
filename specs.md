# X-ray detector

Applikation för detektion av objekt i video med röntgenbilder.
Förutom detektion ska applikationen även ha lägen för att skapa träningsdata och utföra träning av modell.
Planerar att köra applikationen på dator med Windows 11 dit två UVC video capture cards är inkopplade via USB3.0 så att två separata inkommande videoströmmar finns att tillgå.

## Om applikationen
* Ska ha flera lägen i GUI: detektionsläge (default), annoteringsläge och träningsläge
* Bör kunna köras i fullscreen, typ kioskläge
* Ska kunna använda olika detektionsmodeller (t ex YOLO26, RF-DETR, ...)

### Detektionsläge
* Varje videoström körs genom en detektionsmodell och identifierade objekt markeras med rektangel samt med text för identifierad objektklass och sannolikhet
* Visar output från detektionen av de två videoströmmarna i en split screen
* Ha en knapp för att fånga bilder från båda videoströmmarna för att utöka träningsdata
* Vid tryck på fånga sparas aktuella bildrutor från de båda videoströmmarna går man till annoteringsläge med de två bilderna

### Annoteringsläge
* Vy med två frysta bilder (från videoströmmarna) där man väljer klass för identifierat objekt samt ritar rektangel ovanpå varje bild för att bestämma var i respektive bild objektet finns.
* Eventuella befintliga detektioner från detektionsläget vid tidpunkt då fånga-knappen trycktes ska automatiskt ritas in i annoteringsvyn.
* Samtliga inritade rektanglar ska kunna redigeras (storleksändras) genom att trycka och dra i en rektangels kant eller hörn. 
* Samtliga annoterade klasser ska kunna ändras genom att välja annan klass från lista, alternativt skriva in en helt ny klass.
* Spara i annoteringsläget fyller på dataset och återgår till detektionsläge.
* Dataset ska kunna exporteras till COCO alt YOLO format; internt lagras datasetet i YOLO-format, så export behövs inte för träning.
* För exporterat dataset ska det framgå versionssiffra, datum, antal bildobjekt

### Träningsläge
* Startas manuellt där man anger vilken basmodell som ska användas och vilket dataset som ska nyttjas samt träningsparametrar
* Efter avslutad träning sparas modellvikterna med versionssiffra som överenstämmer med det dataset som använts

## Prestanda
* Applikationen behöver fungera utan väntetid för användaren (trådad på lämpligt sätt, träning endast nattetid eller under inaktivitet, osv)
* Under träning kan detektion pausas för att maximera tillgängliga hårdvaruresurser
  

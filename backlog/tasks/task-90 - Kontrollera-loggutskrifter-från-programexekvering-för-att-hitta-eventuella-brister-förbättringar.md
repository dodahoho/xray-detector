---
id: TASK-90
title: >-
  Kontrollera loggutskrifter från programexekvering för att hitta eventuella
  brister/förbättringar
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-16T14:52:00Z'
updated_date: '2026-11-16T16:32:00Z'
labels: []
dependencies: []
type: task
ordinal: 210000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Kolla om loggutskrifter kan ge någon input till förbättringar, fel eller liknande.

Logg från aktuell körning av applikationen:
###
(xray-detector) PS C:\Users\Ai1\repo\xray-detector> uv run python -m xray_detector.app                                                                                                 
W1116 15:09:30.501000 4152 .venv\Lib\site-packages\torch\distributed\elastic\multiprocessing\redirects.py:29] NOTE: Redirects are currently not supported in Windows or MacOs.
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\detr.py:841: FutureWarning: The `RFDETRBase` was deprecated since v1.7.0. It will be removed in v2.0.0.
  getattr(variant_obj, "__name__", symbol): variant_obj
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\detr.py:841: FutureWarning: The `RFDETRLargeDeprecated` was deprecated since v1.7.0. It will be removed in v2.0.0.
  getattr(variant_obj, "__name__", symbol): variant_obj
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\detr.py:841: FutureWarning: The `RFDETRSegPreview` was deprecated since v1.7.0. It will be removed in v2.0.0.
  getattr(variant_obj, "__name__", symbol): variant_obj
[2026-11-16 15:09:30] [WARNING] rf-detr - Using a different number of positional encodings than DINOv2, which means we're not loading DINOv2 backbone weights. This is not a problem if finetuning a pretrained RF-DETR model.
[2026-11-16 15:09:30] [WARNING] rf-detr - Using patch size 16 instead of 14, which means we're not loading DINOv2 backbone weights. This is not a problem if finetuning a pretrained RF-DETR model.
[transformers] `loss_type=None` was set in the config but it is unrecognized. Using the default loss: `ForCausalLMLoss`.
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\backbone\dinov2.py:273: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  assert x.shape[2] % block_size == 0 and x.shape[3] % block_size == 0, (
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\backbone\dinov2_with_windowed_attn.py:442: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if height % divisor != 0 or width % divisor != 0:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\backbone\dinov2_with_windowed_attn.py:327: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if num_channels != self.num_channels:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\backbone\dinov2.py:262: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if num_patches == num_positions and (height, width) == shape:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\backbone\__init__.py:54: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if cross_attn_feats is None and pos.ndim == 4 and pos.shape[1] == 1:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\transformer.py:743: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  topk = min(self.num_queries, enc_outputs_class_unselected_gidx.shape[-2])
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\transformer.py:862: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if refpoint_embed_subset.shape[-2] == 0:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\transformer.py:90: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if pos_tensor.size(-1) == 2:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\transformer.py:92: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  elif pos_tensor.size(-1) == 4:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\torch\__init__.py:2253: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if not condition:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\ops\modules\ms_deform_attn.py:190: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if n_ref_levels not in (1, self.n_levels):
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\ops\modules\ms_deform_attn.py:205: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if n_ref_levels == 1:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\ops\modules\ms_deform_attn.py:207: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  if reference_points.shape[-1] == 2:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\ops\modules\ms_deform_attn.py:214: TracerWarning: Converting a tensor to a Python boolean might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  elif reference_points.shape[-1] == 4:
C:\Users\Ai1\repo\xray-detector\.venv\Lib\site-packages\rfdetr\models\ops\functions\ms_deform_attn_func.py:58: TracerWarning: Converting a tensor to a Python integer might cause the trace to be incorrect. We can't record the data flow of Python values, so this value will be treated as a constant in the future. This means that the trace might not generalize to other inputs!
  value_l_ = value_list[level_index].view(batch_size * n_heads, head_dim, int(height), int(width))
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [ ] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Läs loggkonfigurationen: application/app_config.py (setup_logging, file_logger, rotating_handler), app.py (startordning, message filter, excepthook), ui/crash_dialog.py, ui/main_window.py (_show_status).
2. Läs de faktiska loggfilerna under logs/ och jämför dem med konsolloggen i uppgiften: vilka rader når filen, vilka når bara stderr, vilka loggersystem skriver var.
3. Mappa varje varning i konsolloggen till sin källa och avgör om den är ofarlig eller ett tecken på fel.
4. Verifiera misstänkta fynd empiriskt, t.ex. om testsviten skriver i den riktiga loggkatalogen.
5. Skriv fynden som anteckning med filreferenser och skapa uppföljningsuppgifter för de brister som är värda att åtgärda.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Analys genomförd 2026-11-16 mot konsolloggen i uppgiften och de faktiska filerna under `logs/`.

### Sammanfattning

Varningarna i konsolloggen är alla ofarliga och kommer från tredjepart. Det verkliga problemet är att **ingen av dem når `logs/app.log`**. Appen har tre separata loggsystem som skriver till olika destinationer, så loggfilen är inte en redogörelse för körningen — den är en avskrift av statusraden. Den som får loggfilen skickad sig kan inte se det som stod i konsolen.

### A. Loggfilen saknar det som förklarar problemet

| Källa | Format | Destination |
|---|---|---|
| stdlib logging (appen) | `%(asctime)s %(levelname)s %(name)s: %(message)s` | `logs/app.log` |
| rfdetr:s egen logger | `[%Y-%m-%d %H:%M:%S] [LEVEL] rf-detr - ...` | stderr, med `propagate = False` |
| Python `warnings` (torch, transformers, rfdetr) | rå text | stderr |

`rfdetr/utilities/logger.py` sätter `logger.propagate = False` och egna stream-handlers, så rf-detr-raderna kan aldrig nå root-loggen. `warnings` fångas aldrig eftersom `logging.captureWarnings` inte används någonstans.

Bevis: `logs/app.log` har 183 rader och **noll** TracerWarning, FutureWarning eller rf-detr-rader. Konsolloggen i uppgiften har ett tjugotal av dem, alla vid 15:09:30.

### B. 41 % av app.log är comtypes-brus

76 av 183 rader är `comtypes.client._code_cache` INFO, två per uppstart, i all oändlighet. Root-loggen har ingen nivåstyrning per tredjepartslogger, så allt som propagerar dit hamnar i filen.

### C. Testsviten skriver i den riktiga loggkatalogen

`tests/conftest.py:config` sätter `config.data_dir = tmp_path` men **inte** `logs_dir`, som därför står kvar på `PROJECT_ROOT / "logs"` (`domain/config.py:16`). Fixturens docstring påstår att loggkataloger ligger under `tmp_path` — det stämmer inte.

Verifierat: `pytest tests/test_training_chart.py tests/test_training_pause.py` (26 tester) ökade `logs/training.log` med 5 rader. Samtliga 246 rader i filen är pytest-körningar; det finns ingen riktig träning i den.

### D. Ctrl+C ger en kraschdialog

`logs/app.log` innehåller exakt en ERROR-rad: `Ohanterat undantag: ... KeyboardInterrupt`. `install_exception_dialog` ersätter `sys.excepthook`, som även anropas för `KeyboardInterrupt`. Att avbryta appen med Ctrl+C i en konsol ger alltså "Oväntat fel" med full traceback. `KeyboardInterrupt` bör undantas.

### E. Loggen beskriver statusraden, inte appen

Appens enda loggkanal är `ui/main_window.py:140`, som loggar varje statusradsmeddelande som `status: %s`. 101 av 183 rader är sådana avskrifter. Inget loggar: vilken konfigfil som användes och vad den innehöll, vilken enhet som valdes, vilken viktfil som laddades och hur lång tid det tog, datasetets storlek vid start, kamerauppräkningens resultat eller detektionens FPS.

Gapet mellan `Startar X-ray detector` (15:09:23,671) och `Modell laddad` (15:09:33,548) är tio sekunder som loggen inte förklarar alls — det är precis under dem varningarna skrivs ut.

### F. Ingen varningsstyrning finns

Ingen `warnings.filterwarnings`, `simplefilter` eller `logging.captureWarnings` i appen eller testerna. Förväntade och ofarliga varningar varken dämpas eller fångas: de är brus i konsolen och osynliga i filen.

### G. Varje varning i loggen, med orsak

| Rad i loggen | Orsak | Bedömning |
|---|---|---|
| `torch ... redirects.py:29 NOTE: Redirects are currently not supported in Windows or MacOs` | torch-begränsning på Windows | ofarlig, kan inte åtgärdas |
| `rfdetr/detr.py:841: FutureWarning: The RFDETRBase was deprecated since v1.7.0` (×3) | rfdetr:s egen modul-`__getattr__` vid import | ofarlig, appen orsakar den inte |
| `rf-detr - Using a different number of positional encodings than DINOv2` | förväntat vid finjustering av pretrained RF-DETR | ofarlig |
| `rf-detr - Using patch size 16 instead of 14` | samma | ofarlig |
| `[transformers] loss_type=None ... ForCausalLMLoss` | transformers-konfig, irrelevant för detektion | ofarlig |
| `TracerWarning: Converting a tensor to a Python boolean` (×15) | `torch.jit.trace` inne i rfdetr | ofarlig |

Ingen av dem tyder på ett fel. Problemet är att de inte går att skilja från en verklig varning.

### H. Ingen korrelation mellan app.log och training.log

Två filer utan gemensamt id. Träningsprocessen är en egen OS-process (TASK-6) som skriver till `logs/training.log`, appen till `logs/app.log`. För att följa en träningskörning måste man matcha tidsstämplar för hand.

### I. Loggformatet saknar kontext

`%(asctime)s %(levelname)s %(name)s: %(message)s` innehåller varken process-id eller trådnamn. Eftersom träningen körs i en separat process är det relevant vilken process som skrev raden.

### Åtgärdsförslag, i prioritetsordning

1. Fånga `warnings` till loggen och dämpa de kända ofarliga (torch redirects, rfdetr-depreceringar, TracerWarning, transformers loss_type).
2. Sätt nivå per tredjepartslogger så att `comtypes` och liknande inte hamnar i app.log.
3. Låt `logs_dir` i testfixturen peka under `tmp_path`.
4. Undanta `KeyboardInterrupt` från kraschdialogen.
5. Logga det som faktiskt händer vid uppstart: konfigfil, enhet, modell och laddningstid, datasetstorlek.
6. Ge träningskörningen ett id som finns i både app.log och training.log.
7. Ta med process-id i loggformatet.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Loggen är genomgången och fynden dokumenterade i uppgiftens anteckningar. Slutsatsen är att alla varningar i konsolloggen är ofarliga och kommer från tredjepart — torch:s Windows-begränsning, rfdetr:s deprecerade alias, DINOv2-backbonens patch size (redan utredd i TASK-36), transformers loss_type och torch.jit.trace. Det verkliga problemet är att ingen av dem når logs/app.log: appen har tre loggsystem som skriver till olika destinationer, så loggfilen är en avskrift av statusraden i stället för en redogörelse för körningen. Fyra konkreta brister hittades utöver det: 41 % av app.log är comtypes-brus, testsviten skriver i den riktiga loggkatalogen (verifierat: 26 tester gav 5 nya rader i logs/training.log, och samtliga 246 rader i filen är pytest-körningar), Ctrl+C visar kraschdialogen och loggas som ohanterat undantag, och uppstartens tio sekunder mellan start och modelladdning förklaras inte alls i loggen. Uppföljningsuppgifter skapade: TASK-98 till TASK-101. Verifiering: hela testsviten körd, 667 passed och 1 skipped, oförändrat eftersom ingen kod ändrades. DoD #5 (Code committed) är inte ikryssad: uppgiften producerade ingen kodändring, så det finns inget att committa.
<!-- SECTION:FINAL_SUMMARY:END -->

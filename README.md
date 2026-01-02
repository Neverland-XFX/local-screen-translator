# Local Screen Translator (Windows)

Offline Windows overlay that OCRs a screen region and translates it in real time. Built for games, videos, and UI text.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.

## Features

- ROI selection + always-on-top subtitle overlay
- PaddleOCR (PP-OCRv5) for Japanese/English OCR
- High quality offline translation with NLLB-200 (ja -> zh)
- Optional text-hook mode (clipboard) and YouTube captions bridge
- Context window for recent original/translated lines

## Quick start

1) Create venv and install deps

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Install PaddlePaddle (choose one)

```powershell
# GPU (CUDA 11.8)
python -m pip install paddlepaddle-gpu==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# CPU
python -m pip install paddlepaddle==3.2.2
```

3) Download OCR models (PP-OCRv5 det + rec)

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\download_ppocrv5_models.py
```

4) Download translator models (recommended: NLLB-200)

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\download_ct2_nllb.py
```

5) Run

```powershell
.\.venv\Scripts\Activate.ps1
python .\app\main.py
```

Use last ROI (skip selection):

```powershell
python .\app\main.py --use-last
```

## Modes

- OCR (default): live screen OCR + translation overlay
- Text Hook: reads clipboard (for Textractor, etc.)
- Captions: HTTP bridge for YouTube captions

You can switch modes from the Control window or via `config/default.json` (`input.mode`).

## Translation options

Default translator is NLLB-200 distilled (`facebook/nllb-200-distilled-600M`) with `jpn_Jpan -> zho_Hans`.

Optional fallbacks:
- OPUS-MT cascade (ja->en->zh):

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\download_ct2_opus_mt.py --model Helsinki-NLP/opus-mt-ja-en
python .\scripts\download_ct2_opus_mt.py --model Helsinki-NLP/opus-mt-en-zh
```

- Argos Translate (CPU only, lower quality):

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\install_argos_model.py --from ja --to zh
```

Select engine in `config/default.json`:
- `translate.engine = ct2_nllb | ct2_cascade | ct2 | argos`

## Text hook (Textractor)

Best for visual novels if OCR is too slow or inaccurate.

1) Open Textractor, attach to the game process, and find a working hook.
2) Enable clipboard output (Extensions -> Clipboard).
3) Set `input.mode` to `text_hook_clipboard` or choose `Text Hook` in the Control window.

Useful settings:
- `input.clipboard_poll_ms`
- `input.text_hook_app_path` (restrict to foreground app or folder)
- `input.text_hook_debug`

## YouTube captions bridge

1) Install Tampermonkey.
2) Add `plugins/youtube_caption_bridge.user.js`.
3) Set `input.mode` to `caption_http`.
4) Run the app and enable YouTube captions.

Posts to `http://127.0.0.1:8765/caption`.

## GPU/CUDA notes

- PaddleOCR GPU uses CUDA 11.8 wheels.
- CTranslate2 GPU requires CUDA 12 runtime (`cublas64_12.dll`). If missing, it falls back to CPU int8.
- If you see slow translation, install CUDA 12 runtime or set `translate.*.device = cpu`.

## Tips and troubleshooting

- Waiting for OCR usually means the ROI or monitor index is wrong; reselect ROI on the correct display.
- For games, crop the ROI tightly around the subtitle bar to reduce noise.
- If Windows DPI scaling is not 100%, set `FORCE_DPI_AWARENESS=1` before launching.

## Project layout

```
app/        # main UI + pipeline controller
capture/    # dxcam capture
ocr/        # PaddleOCR/RapidOCR engines
translate/  # CT2 + NLLB translators
ui/         # selection/overlay/control/context windows
config/     # default config (user config is ignored by git)
```

# Local Screen Translator (Windows)

Minimal MVP scaffold for a local screen ROI OCR + translation overlay on Windows.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.

## 1) Create venv + install deps

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install PaddlePaddle (choose one):

```powershell
# GPU (CUDA 11.8)
python -m pip install paddlepaddle-gpu==3.2.2 -i https://www.paddlepaddle.org.cn/packages/stable/cu118/

# CPU
python -m pip install paddlepaddle==3.2.2
```

## 2) Download PP-OCRv5 models (det + rec)

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\download_ppocrv5_models.py
```

## 3) Download & convert NLLB-200 (CTranslate2, high quality)

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\download_ct2_nllb.py
```

## 4) (Optional) Download OPUS-MT fallback (ja->en->zh)

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\download_ct2_opus_mt.py --model Helsinki-NLP/opus-mt-ja-en
python .\scripts\download_ct2_opus_mt.py --model Helsinki-NLP/opus-mt-en-zh
```

## 5) (Optional) Install Argos model (ja -> zh)

```powershell
.\.venv\Scripts\Activate.ps1
python .\scripts\install_argos_model.py --from ja --to zh
```

## 6) Run

```powershell
.\.venv\Scripts\Activate.ps1
python .\app\main.py
```

Use last ROI (skip selection):

```powershell
python .\app\main.py --use-last
```

Notes:
- PP-OCRv5 model files are downloaded into `models/ocr/ppocrv5_server_det` and `models/ocr/ppocrv5_server_rec`.
- If you want to switch back to RapidOCR ONNX, update `config/default.json` and place ONNX models under `models/ocr/`.
- To use GPU with PaddleOCR, install `paddlepaddle-gpu` and set `"device": "gpu"` in `config/default.json`.
- Default translator is NLLB-200 distilled (`facebook/nllb-200-distilled-600M`) with `jpn_Jpan -> zho_Hans`.
- There is no direct OPUS `ja->zh` model; OPUS fallback uses `ja->en` then `en->zh` in a cascade.
- CTranslate2 uses models converted by `scripts/download_ct2_nllb.py` or `scripts/download_ct2_opus_mt.py`.
- If CTranslate2 fails to initialize on GPU (missing CUDA 12 runtime), it will fall back to CPU int8 automatically.
- A floating Context window shows recent OCR + translations; toggle it with the `Context` button.
- Sentence buffering merges consecutive subtitle fragments and only translates once a sentence is complete or times out.
- When `split_on_no_overlap` is enabled, a new unrelated subtitle will force-flush the previous sentence even without punctuation.
- DPI scaling issues can cause ROI offset. Keep Windows scaling at 100% until DPI handling is tuned.
- Input mode can be switched from the Control window (OCR, Text Hook, Captions) or by editing `input.mode` in `config/default.json`.

## Game text hook (Textractor)

For Japanese games, the most accurate approach is a text hook (no OCR). Use Textractor to copy game text to the clipboard.

1) Launch Textractor, attach to the game process, and pick a working hook.
2) Enable its clipboard output (Extensions -> Clipboard).
3) Set `input.mode` to `text_hook_clipboard` or select `Text Hook` in the Control window.
4) Run the app and keep Textractor active; new clipboard text will be translated.

`input.clipboard_poll_ms` controls how frequently the clipboard is read.
`input.text_hook_app_path` can restrict translations to when the target game is the foreground window (no embedded changes; just a foreground process path check). If you point it to a folder, any exe under that folder will match.
`input.text_hook_debug` shows status updates when clipboard text is received.

## YouTube captions plugin (no OCR)

If you want accurate captions without OCR, you can use a userscript to send YouTube captions to the app.

1) Install Tampermonkey (Chrome/Edge).
2) Add the script at `plugins/youtube_caption_bridge.user.js`.
3) Set `input.mode` to `caption_http` in `config/default.json`.
4) Run the app and enable YouTube captions.

The script posts captions to `http://127.0.0.1:8765/caption`.

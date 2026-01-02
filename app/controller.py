import queue
import re
import threading
import time

import cv2
import numpy as np
from PySide6 import QtCore, QtGui

from capture.dxcam_backend import DXCamCapture
from input.caption_server import CaptionServer
from input.clipboard_watcher import ClipboardWatcher
from ocr.paddleocr_engine import PaddleOCREngine
from ocr.rapidocr_engine import RapidOCREngine
from translate.argos_engine import ArgosTranslator
from translate.ct2_cascade import CT2CascadeTranslator
from translate.ct2_engine import CT2Translator
from translate.ct2_nllb import CT2NLLBTranslator
from utils.cache import LRUCache
from utils.sentence_buffer import SentenceBuffer
from utils.text import normalize_text, similarity
from utils.win_process import get_foreground_process_path, paths_match


class PipelineController(QtCore.QObject):
    translation_ready = QtCore.Signal(str)
    translation_pair = QtCore.Signal(str, str)
    ocr_ready = QtCore.Signal(str)
    status = QtCore.Signal(str)

    def __init__(self, config: dict) -> None:
        super().__init__()
        self._config = config
        self._capture = None
        self._ocr_engine = None
        self._translator = None
        self._translate_cfg = None
        self._input_mode = "ocr"
        self._caption_server = None
        self._external_queue = None
        self._external_thread = None
        self._clipboard_watcher = None
        self._text_hook_path = ""
        self._text_hook_require_foreground = True
        self._text_hook_re = None
        self._text_hook_debug = False
        self._text_hook_status_last = ""
        self._threads = []
        self._stop_event = threading.Event()
        self._text_queue = None
        self._cache = None
        self._last_ocr_text = ""
        self._sentence_buffer = None

    def start(self, roi_logical) -> None:
        self.stop()
        self._stop_event.clear()
        self._last_ocr_text = ""
        self._text_queue = queue.Queue(maxsize=1)

        translate_cfg = self._config["translate"]
        self._translate_cfg = translate_cfg
        self._translator = self._create_translator(translate_cfg)
        if self._translator.error:
            self.status.emit(f"Translate init failed: {self._translator.error}")
        else:
            if isinstance(self._translator, (CT2Translator, CT2CascadeTranslator, CT2NLLBTranslator)):
                self.status.emit(
                    f"Translator: CT2 {self._translator.device}/{self._translator.compute_type}"
                )
            else:
                self.status.emit("Translator: Argos")

        cache_cfg = self._config["pipeline"]["cache"]
        self._cache = LRUCache(max_entries=cache_cfg["max_entries"])

        sb_cfg = self._config["pipeline"].get("sentence_buffer", {})
        if sb_cfg.get("enabled", True):
            self._sentence_buffer = SentenceBuffer(
                merge_gap_ms=sb_cfg.get("merge_gap_ms", 1200),
                max_hold_ms=sb_cfg.get("max_hold_ms", 2500),
                max_chars=sb_cfg.get("max_chars", 300),
                min_overlap=sb_cfg.get("min_overlap", 6),
                end_punct=sb_cfg.get("end_punct", ".!?…"),
                split_on_no_overlap=sb_cfg.get("split_on_no_overlap", True),
                split_similarity=sb_cfg.get("split_similarity", 0.6),
            )
        else:
            self._sentence_buffer = None

        input_cfg = self._config.get("input", {})
        self._input_mode = input_cfg.get("mode", "ocr")

        if self._input_mode == "caption_http":
            port = int(input_cfg.get("caption_port", 8765))
            self._external_queue = queue.Queue(maxsize=5)
            self._caption_server = CaptionServer(
                host="127.0.0.1", port=port, on_text=self._on_external_text
            )
            self._caption_server.start()
            self.status.emit(f"Caption server: http://127.0.0.1:{port}/caption")

            self._external_thread = threading.Thread(
                target=self._external_loop, daemon=True
            )
            self._external_thread.start()
        elif self._input_mode == "text_hook_clipboard":
            poll_ms = int(input_cfg.get("clipboard_poll_ms", 120))
            self._external_queue = queue.Queue(maxsize=5)
            self._clipboard_watcher = ClipboardWatcher(
                poll_ms=poll_ms, on_text=self._on_external_text
            )
            self._clipboard_watcher.start()
            self._text_hook_path = str(input_cfg.get("text_hook_app_path", "")).strip()
            self._text_hook_require_foreground = bool(
                input_cfg.get("text_hook_require_foreground", True)
            )
            regex = str(input_cfg.get("text_hook_regex", "")).strip()
            self._text_hook_re = None
            if regex:
                try:
                    self._text_hook_re = re.compile(regex)
                except re.error as exc:
                    self.status.emit(f"Text hook regex invalid: {exc}")
            self._text_hook_status_last = ""
            self._text_hook_debug = bool(input_cfg.get("text_hook_debug", False))
            label = self._text_hook_path or "any app"
            self.status.emit(f"Text hook: clipboard (poll {poll_ms} ms, filter {label})")

            self._external_thread = threading.Thread(
                target=self._external_loop, daemon=True
            )
            self._external_thread.start()
        else:
            roi_physical = self._logical_to_physical_rect(roi_logical)
            capture_cfg = self._config["capture"]
            self._capture = DXCamCapture(
                monitor_index=capture_cfg["monitor_index"],
                target_fps=capture_cfg["target_fps"],
            )
            self._capture.start(roi_physical)

            self._ocr_engine = self._create_ocr_engine(self._config["ocr"])
            if self._ocr_engine.error:
                self.status.emit(f"OCR init failed: {self._ocr_engine.error}")

            ocr_thread = threading.Thread(target=self._ocr_loop, daemon=True)
            ocr_thread.start()
            self._threads.append(ocr_thread)

        if not self._translator.error:
            translate_thread = threading.Thread(target=self._translate_loop, daemon=True)
            translate_thread.start()
            self._threads.append(translate_thread)

    def stop(self) -> None:
        self._stop_event.set()
        for thread in self._threads:
            thread.join(timeout=1.0)
        self._threads = []
        if self._capture:
            self._capture.stop()
        self._capture = None
        if self._caption_server:
            self._caption_server.stop()
        self._caption_server = None
        if self._clipboard_watcher:
            self._clipboard_watcher.stop()
        self._clipboard_watcher = None
        if self._external_thread:
            self._external_thread.join(timeout=1.0)
        self._external_thread = None
        self._external_queue = None
        self._text_hook_path = ""
        self._text_hook_require_foreground = True
        self._text_hook_re = None
        self._text_hook_debug = False
        self._text_hook_status_last = ""

    def _ocr_loop(self) -> None:
        if not self._ocr_engine or self._ocr_engine.error:
            return

        pipeline_cfg = self._config["pipeline"]
        ocr_interval = pipeline_cfg["ocr_interval_ms"] / 1000.0
        change_cfg = pipeline_cfg["change_detect"]
        debounce_cfg = pipeline_cfg["debounce"]
        sim_threshold = debounce_cfg["text_similarity_threshold"]

        last_small = None

        while not self._stop_event.is_set():
            time.sleep(ocr_interval)
            now = time.time()
            frame = self._capture.get_latest_frame() if self._capture else None
            if frame is None:
                if self._sentence_buffer:
                    for sentence in self._sentence_buffer.flush_if_timeout(now):
                        self._push_latest_text(sentence)
                continue

            gray = self._to_gray(frame)
            if change_cfg["enabled"]:
                small = cv2.resize(
                    gray,
                    (change_cfg["downsample"], change_cfg["downsample"]),
                    interpolation=cv2.INTER_AREA,
                )
                if last_small is not None:
                    mad = np.mean(cv2.absdiff(small, last_small))
                    if mad < change_cfg["mad_threshold"]:
                        last_small = small
                        continue
                last_small = small

            bgr = self._to_bgr(frame)
            raw_text, error = self._ocr_engine.recognize_text(bgr)
            if error:
                self.status.emit(f"OCR error: {error}")
                continue

            normalized = normalize_text(raw_text)
            if not normalized:
                if self._sentence_buffer:
                    for sentence in self._sentence_buffer.flush_if_timeout(now):
                        self._push_latest_text(sentence)
                continue

            if similarity(normalized, self._last_ocr_text) >= sim_threshold:
                if self._sentence_buffer:
                    for sentence in self._sentence_buffer.flush_if_timeout(now):
                        self._push_latest_text(sentence)
                continue

            self._last_ocr_text = normalized
            self.ocr_ready.emit(normalized)
            if self._sentence_buffer:
                for sentence in self._sentence_buffer.update(normalized, now):
                    self._push_latest_text(sentence)
            else:
                self._push_latest_text(normalized)

    def _external_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                text = self._external_queue.get(timeout=0.2)
                now = time.time()
            except queue.Empty:
                if self._sentence_buffer:
                    for sentence in self._sentence_buffer.flush_if_timeout(time.time()):
                        self._push_latest_text(sentence)
                continue

            normalized = normalize_text(text)
            if not normalized:
                continue

            if normalized == self._last_ocr_text:
                continue
            if self._input_mode == "text_hook_clipboard" and not self._text_hook_allows(normalized):
                continue

            self._last_ocr_text = normalized
            self.ocr_ready.emit(normalized)
            if self._sentence_buffer:
                for sentence in self._sentence_buffer.update(normalized, now):
                    self._push_latest_text(sentence)
            else:
                self._push_latest_text(normalized)

    def _text_hook_allows(self, text: str) -> bool:
        if self._text_hook_re and not self._text_hook_re.search(text):
            self._emit_text_hook_status("Text hook blocked: regex filter")
            return False
        if not self._text_hook_path:
            return True
        fg_path = get_foreground_process_path()
        if fg_path and paths_match(fg_path, self._text_hook_path):
            return True
        if self._text_hook_require_foreground:
            if fg_path:
                self._emit_text_hook_status(f"Text hook blocked: foreground {fg_path}")
            else:
                self._emit_text_hook_status("Text hook blocked: foreground unknown")
            return False
        return True

    def _emit_text_hook_status(self, message: str) -> None:
        if not message or message == self._text_hook_status_last:
            return
        self._text_hook_status_last = message
        self.status.emit(message)

    def _translate_loop(self) -> None:
        min_interval = self._config["pipeline"]["debounce"]["min_translate_interval_ms"] / 1000.0
        last_time = 0.0

        while not self._stop_event.is_set():
            try:
                text = self._text_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            now = time.time()
            elapsed = now - last_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

            cached = self._cache.get(text) if self._cache else None
            if cached:
                self.translation_ready.emit(cached)
                last_time = time.time()
                continue

            translation, error = self._translator.translate(text)
            if error:
                if self._maybe_fallback_translator(error):
                    translation, error = self._translator.translate(text)
                if error:
                    self.status.emit(f"Translate error: {error}")
                    continue
            if self._cache:
                self._cache.set(text, translation)
            self.translation_ready.emit(translation)
            self.translation_pair.emit(text, translation)
            last_time = time.time()

    def _push_latest_text(self, text: str) -> None:
        try:
            _ = self._text_queue.get_nowait()
        except queue.Empty:
            pass
        try:
            self._text_queue.put_nowait(text)
        except queue.Full:
            pass

    def _to_gray(self, frame):
        if frame.ndim == 3 and frame.shape[2] == 4:
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def _to_bgr(self, frame):
        if frame.ndim == 3 and frame.shape[2] == 4:
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame

    def _logical_to_physical_rect(self, rect):
        left, top, right, bottom = rect
        screen = QtGui.QGuiApplication.screenAt(QtCore.QPoint(left, top))
        if not screen:
            screen = QtGui.QGuiApplication.primaryScreen()
        dpr = screen.devicePixelRatio()
        geom = screen.geometry()
        left -= geom.left()
        right -= geom.left()
        top -= geom.top()
        bottom -= geom.top()
        return (
            int(round(left * dpr)),
            int(round(top * dpr)),
            int(round(right * dpr)),
            int(round(bottom * dpr)),
        )

    def _on_external_text(self, text: str) -> None:
        if not self._external_queue:
            return
        if self._text_hook_debug and text:
            self._emit_text_hook_status(f"Text hook received {len(text)} chars")
        try:
            self._external_queue.put_nowait(text)
        except queue.Full:
            try:
                _ = self._external_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._external_queue.put_nowait(text)
            except queue.Full:
                pass

    def _create_ocr_engine(self, ocr_cfg: dict):
        engine_name = ocr_cfg.get("engine", "rapidocr_onnxruntime")
        if engine_name == "paddleocr":
            paddle_cfg = ocr_cfg.get("paddle", {})
            return PaddleOCREngine(
                det_model_dir=paddle_cfg.get("det_model_dir", ""),
                rec_model_dir=paddle_cfg.get("rec_model_dir", ""),
                device=paddle_cfg.get("device", "cpu"),
            )

        return RapidOCREngine(
            det_model_path=ocr_cfg["det_model_path"],
            rec_model_path=ocr_cfg["rec_model_path"],
            box_thresh=ocr_cfg["box_thresh"],
            unclip_ratio=ocr_cfg["unclip_ratio"],
            text_score=ocr_cfg["text_score"],
        )

    def _create_translator(self, translate_cfg: dict):
        engine_name = translate_cfg.get("engine", "argos")
        if engine_name == "ct2_nllb":
            nllb_cfg = translate_cfg.get("ct2_nllb", {})
            lang_cfg = translate_cfg.get("nllb", {})
            translator = CT2NLLBTranslator(
                model_dir=nllb_cfg.get("model_dir", ""),
                tokenizer_dir=nllb_cfg.get("tokenizer_dir"),
                source_lang=lang_cfg.get("source_lang", "jpn_Jpan"),
                target_lang=lang_cfg.get("target_lang", "zho_Hans"),
                device=nllb_cfg.get("device", "cpu"),
                compute_type=nllb_cfg.get("compute_type", "float32"),
                beam_size=nllb_cfg.get("beam_size", 1),
                max_batch_size=nllb_cfg.get("max_batch_size", 1),
            )
            if translator.error and nllb_cfg.get("device", "cpu") in ("cuda", "gpu"):
                self.status.emit(
                    "CT2 NLLB GPU init failed; falling back to CPU (int8)."
                )
                return CT2NLLBTranslator(
                    model_dir=nllb_cfg.get("model_dir", ""),
                    tokenizer_dir=nllb_cfg.get("tokenizer_dir"),
                    source_lang=lang_cfg.get("source_lang", "jpn_Jpan"),
                    target_lang=lang_cfg.get("target_lang", "zho_Hans"),
                    device="cpu",
                    compute_type="int8",
                    beam_size=nllb_cfg.get("beam_size", 1),
                    max_batch_size=nllb_cfg.get("max_batch_size", 1),
                )
            return translator

        if engine_name == "ct2_cascade":
            cascade_cfg = translate_cfg.get("ct2_cascade", {})
            translator = CT2CascadeTranslator(
                first_model_dir=cascade_cfg.get("first_model_dir", ""),
                second_model_dir=cascade_cfg.get("second_model_dir", ""),
                first_tokenizer_dir=cascade_cfg.get("first_tokenizer_dir"),
                second_tokenizer_dir=cascade_cfg.get("second_tokenizer_dir"),
                device=cascade_cfg.get("device", "cpu"),
                compute_type=cascade_cfg.get("compute_type", "float32"),
                beam_size=cascade_cfg.get("beam_size", 1),
                max_batch_size=cascade_cfg.get("max_batch_size", 1),
            )
            if translator.error and cascade_cfg.get("device", "cpu") in ("cuda", "gpu"):
                self.status.emit(
                    "CT2 cascade GPU init failed; falling back to CPU (int8)."
                )
                return CT2CascadeTranslator(
                    first_model_dir=cascade_cfg.get("first_model_dir", ""),
                    second_model_dir=cascade_cfg.get("second_model_dir", ""),
                    first_tokenizer_dir=cascade_cfg.get("first_tokenizer_dir"),
                    second_tokenizer_dir=cascade_cfg.get("second_tokenizer_dir"),
                    device="cpu",
                    compute_type="int8",
                    beam_size=cascade_cfg.get("beam_size", 1),
                    max_batch_size=cascade_cfg.get("max_batch_size", 1),
                )
            return translator

        if engine_name == "ct2":
            ct2_cfg = translate_cfg.get("ct2", {})
            translator = CT2Translator(
                model_dir=ct2_cfg.get("model_dir", ""),
                tokenizer_dir=ct2_cfg.get("tokenizer_dir"),
                device=ct2_cfg.get("device", "cpu"),
                compute_type=ct2_cfg.get("compute_type", "float32"),
                beam_size=ct2_cfg.get("beam_size", 1),
                max_batch_size=ct2_cfg.get("max_batch_size", 1),
            )
            if translator.error and ct2_cfg.get("device", "cpu") in ("cuda", "gpu"):
                self.status.emit(
                    "CT2 GPU init failed; falling back to CPU (int8)."
                )
                return CT2Translator(
                    model_dir=ct2_cfg.get("model_dir", ""),
                    tokenizer_dir=ct2_cfg.get("tokenizer_dir"),
                    device="cpu",
                    compute_type="int8",
                    beam_size=ct2_cfg.get("beam_size", 1),
                    max_batch_size=ct2_cfg.get("max_batch_size", 1),
                )
            return translator

        return ArgosTranslator(
            from_code=translate_cfg.get("from", "en"),
            to_code=translate_cfg.get("to", "zh"),
            device_type=translate_cfg.get("argos_device_type", "cpu"),
        )

    def _maybe_fallback_translator(self, error: str) -> bool:
        if not isinstance(self._translator, (CT2Translator, CT2CascadeTranslator, CT2NLLBTranslator)):
            return False
        if not self._translate_cfg:
            return False
        if self._translator.device not in ("cuda", "gpu"):
            return False

        err_lower = error.lower()
        if "cublas64_12" not in err_lower and "cuda" not in err_lower and "cudnn" not in err_lower:
            return False

        if isinstance(self._translator, CT2Translator):
            ct2_cfg = self._translate_cfg.get("ct2", {})
            self.status.emit("CT2 GPU runtime missing; switching to CPU int8.")
            self._translator = CT2Translator(
                model_dir=ct2_cfg.get("model_dir", ""),
                tokenizer_dir=ct2_cfg.get("tokenizer_dir"),
                device="cpu",
                compute_type="int8",
                beam_size=ct2_cfg.get("beam_size", 1),
                max_batch_size=ct2_cfg.get("max_batch_size", 1),
            )
            return self._translator.error is None

        if isinstance(self._translator, CT2CascadeTranslator):
            cascade_cfg = self._translate_cfg.get("ct2_cascade", {})
            self.status.emit("CT2 cascade GPU runtime missing; switching to CPU int8.")
            self._translator = CT2CascadeTranslator(
                first_model_dir=cascade_cfg.get("first_model_dir", ""),
                second_model_dir=cascade_cfg.get("second_model_dir", ""),
                first_tokenizer_dir=cascade_cfg.get("first_tokenizer_dir"),
                second_tokenizer_dir=cascade_cfg.get("second_tokenizer_dir"),
                device="cpu",
                compute_type="int8",
                beam_size=cascade_cfg.get("beam_size", 1),
                max_batch_size=cascade_cfg.get("max_batch_size", 1),
            )
            return self._translator.error is None

        nllb_cfg = self._translate_cfg.get("ct2_nllb", {})
        lang_cfg = self._translate_cfg.get("nllb", {})
        self.status.emit("CT2 NLLB GPU runtime missing; switching to CPU int8.")
        self._translator = CT2NLLBTranslator(
            model_dir=nllb_cfg.get("model_dir", ""),
            tokenizer_dir=nllb_cfg.get("tokenizer_dir"),
            source_lang=lang_cfg.get("source_lang", "jpn_Jpan"),
            target_lang=lang_cfg.get("target_lang", "zho_Hans"),
            device="cpu",
            compute_type="int8",
            beam_size=nllb_cfg.get("beam_size", 1),
            max_batch_size=nllb_cfg.get("max_batch_size", 1),
        )
        return self._translator.error is None

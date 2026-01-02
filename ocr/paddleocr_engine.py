from pathlib import Path
import os

os.environ.setdefault("DISABLE_MODEL_SOURCE_CHECK", "true")

from paddleocr import PaddleOCR

from utils.paths import resolve_path


class PaddleOCREngine:
    def __init__(self, det_model_dir: str, rec_model_dir: str, device: str = "cpu") -> None:
        self._ocr = None
        self._error = None

        try:
            det_dir = self._resolve_dir(det_model_dir)
            rec_dir = self._resolve_dir(rec_model_dir)
            self._ocr = PaddleOCR(
                text_detection_model_dir=det_dir,
                text_recognition_model_dir=rec_dir,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                device=device,
            )
        except Exception as exc:
            self._error = str(exc)

    def _resolve_dir(self, dir_path: str) -> str:
        if not dir_path:
            raise FileNotFoundError("Model directory is empty.")
        path = resolve_path(dir_path)
        if not Path(path).exists():
            raise FileNotFoundError(f"Model directory not found: {path}")
        return str(path)

    @property
    def error(self):
        return self._error

    def recognize_text(self, image_bgr):
        if not self._ocr:
            return "", self._error
        try:
            result = self._ocr.ocr(image_bgr)
            text = self._extract_text(result)
            return text, None
        except Exception as exc:
            return "", str(exc)

    def _extract_text(self, result) -> str:
        if not result:
            return ""

        if isinstance(result, list) and result and isinstance(result[0], dict):
            texts = []
            for item in result:
                texts.extend(item.get("rec_texts", []) or [])
            return "\n".join(texts)

        candidates = result
        if (
            isinstance(result, list)
            and len(result) == 1
            and isinstance(result[0], list)
            and result[0]
            and isinstance(result[0][0], (list, tuple))
        ):
            candidates = result[0]

        lines = []
        for line in candidates:
            if not isinstance(line, (list, tuple)) or len(line) < 2:
                continue
            text_part = line[1]
            if isinstance(text_part, (list, tuple)) and text_part:
                text = text_part[0]
            else:
                text = str(text_part)
            if text:
                lines.append(text)

        return "\n".join(lines)

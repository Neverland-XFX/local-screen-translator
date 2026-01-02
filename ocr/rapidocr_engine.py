from pathlib import Path

from rapidocr_onnxruntime import RapidOCR

from utils.paths import resolve_path
from ocr.postprocess import ocr_result_to_text


class RapidOCREngine:
    def __init__(
        self,
        det_model_path: str,
        rec_model_path: str,
        rec_img_shape=(3, 48, 320),
        box_thresh: float = 0.5,
        unclip_ratio: float = 1.6,
        text_score: float = 0.5,
    ) -> None:
        self._engine = None
        self._error = None
        self._params = {
            "box_thresh": box_thresh,
            "unclip_ratio": unclip_ratio,
            "text_score": text_score,
        }

        try:
            det_path = self._resolve_model(det_model_path)
            rec_path = self._resolve_model(rec_model_path)
            self._engine = RapidOCR(
                det_model_path=det_path,
                rec_model_path=rec_path,
                rec_img_shape=list(rec_img_shape),
            )
        except Exception as exc:
            self._error = str(exc)

    def _resolve_model(self, model_path: str) -> str:
        if not model_path:
            return ""
        path = resolve_path(model_path)
        if not Path(path).exists():
            raise FileNotFoundError(f"Model not found: {path}")
        return str(path)

    @property
    def error(self):
        return self._error

    def recognize(self, image_bgr):
        if not self._engine:
            return None, self._error
        result, _ = self._engine(image_bgr, **self._params)
        return result, None

    def recognize_text(self, image_bgr):
        result, error = self.recognize(image_bgr)
        if error or not result:
            return "", error
        return ocr_result_to_text(result), None

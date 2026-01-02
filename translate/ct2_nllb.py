from pathlib import Path

import ctranslate2
from transformers import AutoTokenizer

from utils.paths import resolve_path


class CT2NLLBTranslator:
    def __init__(
        self,
        model_dir: str,
        tokenizer_dir: str | None = None,
        source_lang: str = "jpn_Jpan",
        target_lang: str = "zho_Hans",
        device: str = "cpu",
        compute_type: str = "float32",
        beam_size: int = 1,
        max_batch_size: int = 1,
    ) -> None:
        self._translator = None
        self._tokenizer = None
        self._error = None
        self._model_dir = model_dir
        self._tokenizer_dir = tokenizer_dir
        self._device = device
        self._compute_type = compute_type
        self._beam_size = beam_size
        self._max_batch_size = max_batch_size
        self._source_lang = source_lang
        self._target_lang = target_lang
        self._target_token = None

        try:
            model_path = self._resolve_dir(model_dir)
            tokenizer_path = self._resolve_dir(tokenizer_dir) if tokenizer_dir else model_path

            self._tokenizer = self._load_tokenizer(str(tokenizer_path))
            self._validate_lang_code(source_lang, "source")
            self._validate_lang_code(target_lang, "target")
            if hasattr(self._tokenizer, "src_lang"):
                self._tokenizer.src_lang = source_lang
            self._target_token = target_lang
            self._translator = ctranslate2.Translator(
                str(model_path), device=device, compute_type=compute_type
            )
        except Exception as exc:
            self._error = str(exc)

    def _resolve_dir(self, path_str: str) -> Path:
        if not path_str:
            raise FileNotFoundError("Model directory is empty.")
        path = resolve_path(path_str)
        if not Path(path).exists():
            raise FileNotFoundError(f"Model directory not found: {path}")
        return Path(path)

    @property
    def error(self):
        return self._error

    @property
    def device(self):
        return self._device

    @property
    def compute_type(self):
        return self._compute_type

    def _load_tokenizer(self, path: str):
        try:
            return AutoTokenizer.from_pretrained(path, use_fast=False)
        except Exception:
            try:
                return AutoTokenizer.from_pretrained(
                    path, use_fast=True, fix_mistral_regex=True
                )
            except TypeError:
                return AutoTokenizer.from_pretrained(path, use_fast=True)

    def _validate_lang_code(self, lang_code: str, label: str) -> None:
        token_id = self._tokenizer.convert_tokens_to_ids(lang_code)
        unk_id = getattr(self._tokenizer, "unk_token_id", None)
        if token_id is None or token_id == unk_id:
            raise ValueError(f"Unsupported {label}_lang: {lang_code}")

    def translate(self, text: str):
        if not self._translator or not self._tokenizer:
            return None, self._error
        try:
            if hasattr(self._tokenizer, "src_lang"):
                self._tokenizer.src_lang = self._source_lang
            tokens = self._tokenizer.convert_ids_to_tokens(
                self._tokenizer.encode(text, add_special_tokens=True)
            )
            target_prefix = [[self._target_token]] if self._target_token else None
            results = self._translator.translate_batch(
                [tokens],
                target_prefix=target_prefix,
                beam_size=self._beam_size,
                max_batch_size=self._max_batch_size,
            )
            out_tokens = results[0].hypotheses[0]
            out_ids = self._tokenizer.convert_tokens_to_ids(out_tokens)
            out_text = self._tokenizer.decode(out_ids, skip_special_tokens=True)
            return out_text, None
        except Exception as exc:
            return None, str(exc)

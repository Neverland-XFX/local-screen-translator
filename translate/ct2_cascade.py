from translate.ct2_engine import CT2Translator


class CT2CascadeTranslator:
    def __init__(
        self,
        first_model_dir: str,
        second_model_dir: str,
        first_tokenizer_dir: str | None = None,
        second_tokenizer_dir: str | None = None,
        device: str = "cpu",
        compute_type: str = "float32",
        beam_size: int = 1,
        max_batch_size: int = 1,
    ) -> None:
        self._first = CT2Translator(
            model_dir=first_model_dir,
            tokenizer_dir=first_tokenizer_dir,
            device=device,
            compute_type=compute_type,
            beam_size=beam_size,
            max_batch_size=max_batch_size,
        )
        self._second = CT2Translator(
            model_dir=second_model_dir,
            tokenizer_dir=second_tokenizer_dir,
            device=device,
            compute_type=compute_type,
            beam_size=beam_size,
            max_batch_size=max_batch_size,
        )
        self._error = self._first.error or self._second.error
        self._device = device
        self._compute_type = compute_type

    @property
    def error(self):
        return self._error

    @property
    def device(self):
        return self._device

    @property
    def compute_type(self):
        return self._compute_type

    def translate(self, text: str):
        if self._error:
            return None, self._error
        mid, err = self._first.translate(text)
        if err:
            return None, f"stage1: {err}"
        out, err = self._second.translate(mid)
        if err:
            return None, f"stage2: {err}"
        return out, None

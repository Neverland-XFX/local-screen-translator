import os

import argostranslate.translate


class ArgosTranslator:
    def __init__(self, from_code: str = "en", to_code: str = "zh", device_type: str = "cpu") -> None:
        os.environ.setdefault("ARGOS_DEVICE_TYPE", device_type)
        self._translator = None
        self._error = None

        try:
            languages = argostranslate.translate.get_installed_languages()
            from_lang = next((l for l in languages if l.code == from_code), None)
            to_lang = next((l for l in languages if l.code == to_code), None)
            if not from_lang or not to_lang:
                self._error = "Argos model not installed. Run scripts/install_argos_model.py"
                return
            self._translator = from_lang.get_translation(to_lang)
            if not self._translator:
                self._error = "Argos translation pair not available."
        except Exception as exc:
            self._error = str(exc)

    @property
    def error(self):
        return self._error

    def translate(self, text: str):
        if not self._translator:
            return None, self._error
        try:
            return self._translator.translate(text), None
        except Exception as exc:
            return None, str(exc)

import re
from difflib import SequenceMatcher


_whitespace_re = re.compile(r"\s+")
_cjk_re = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uF900-\uFAFF]")


def normalize_text(text: str) -> str:
    text = text.replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    joiner = "" if _cjk_re.search("".join(lines)) else " "
    compact = joiner.join(lines)
    return _whitespace_re.sub(" ", compact).strip()


def similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()

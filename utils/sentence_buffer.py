import re
from difflib import SequenceMatcher


class SentenceBuffer:
    def __init__(
        self,
        merge_gap_ms: int = 1200,
        max_hold_ms: int = 2500,
        max_chars: int = 300,
        min_overlap: int = 6,
        end_punct: str = ".!?…",
        split_on_no_overlap: bool = True,
        split_similarity: float = 0.6,
    ) -> None:
        self._merge_gap = merge_gap_ms / 1000.0
        self._max_hold = max_hold_ms / 1000.0 if max_hold_ms > 0 else 0.0
        self._max_chars = max_chars
        self._min_overlap = min_overlap
        self._split_on_no_overlap = split_on_no_overlap
        self._split_similarity = split_similarity
        tail_chars = "\"')\\]」』】》）"
        self._end_re = re.compile(
            rf"[{re.escape(end_punct)}]+[{re.escape(tail_chars)}]*$"
        )
        self._buffer = ""
        self._last_change = 0.0

    def update(self, text: str, now: float) -> list[str]:
        sentences = []
        text = text.strip()
        if not text:
            return sentences

        if not self._buffer:
            self._buffer = text
            self._last_change = now
            if self._is_complete(self._buffer):
                sentences.append(self._buffer)
                self.clear()
            return sentences

        if now - self._last_change > self._merge_gap:
            sentences.append(self._buffer)
            self.clear()

        if not self._buffer:
            self._buffer = text
            self._last_change = now
            if self._is_complete(self._buffer):
                sentences.append(self._buffer)
                self.clear()
            return sentences

        overlap = self._overlap_len(self._buffer, text)
        if overlap < self._min_overlap and self._split_on_no_overlap:
            if self._similarity(self._buffer, text) < self._split_similarity:
                sentences.append(self._buffer)
                self._buffer = text
                self._last_change = now
                if self._is_complete(self._buffer):
                    sentences.append(self._buffer)
                    self.clear()
                return sentences

        merged = self._merge(self._buffer, text, overlap)
        if merged != self._buffer:
            self._buffer = merged
            self._last_change = now

        if self._is_complete(self._buffer) or len(self._buffer) >= self._max_chars:
            sentences.append(self._buffer)
            self.clear()
        return sentences

    def flush_if_timeout(self, now: float) -> list[str]:
        if self._max_hold <= 0:
            return []
        if not self._buffer:
            return []
        if now - self._last_change >= self._max_hold:
            sentence = self._buffer
            self.clear()
            return [sentence]
        return []

    def clear(self) -> None:
        self._buffer = ""
        self._last_change = 0.0

    def _is_complete(self, text: str) -> bool:
        return bool(self._end_re.search(text))

    def _overlap_len(self, prev: str, new: str) -> int:
        if new.startswith(prev):
            return len(prev)
        if prev.startswith(new):
            return len(new)

        prev_lower = prev.lower()
        new_lower = new.lower()
        max_k = min(len(prev_lower), len(new_lower))
        for k in range(max_k, self._min_overlap - 1, -1):
            if prev_lower[-k:] == new_lower[:k]:
                return k
        return 0

    def _merge(self, prev: str, new: str, overlap_len: int) -> str:
        if new.startswith(prev):
            return new
        if prev.startswith(new):
            return prev
        if overlap_len >= self._min_overlap:
            return prev + new[overlap_len:]

        sep = "" if prev.endswith(" ") or new.startswith(" ") else " "
        return prev + sep + new

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()

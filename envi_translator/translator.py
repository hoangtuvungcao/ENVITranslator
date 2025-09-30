from __future__ import annotations

import re
import time
from typing import Dict, List, Optional, Union

from deep_translator import GoogleTranslator


class ENVITranslator:
    """Simple wrapper around deep-translator's GoogleTranslator for EN ↔ VI."""

    def __init__(self, source: str = "auto", target: str = "vi") -> None:
        norm_source = self._normalize_lang(source)
        norm_target = self._normalize_lang(target)
        self.source = norm_source
        self.target = norm_target
        self._translator = GoogleTranslator(source=norm_source, target=norm_target)

    def translate_text(
        self,
        text: str,
        *,
        preserve_format: bool = True,
        max_chars: int = 4500,
        retries: int = 3,
        retry_backoff_sec: float = 1.0,
    ) -> str:
        """Translate a text string with optional formatting preservation.

        - preserve_format: when True, keeps line breaks and spacing as much as possible.
        - max_chars: safe size for each chunk to avoid provider limits.
        - retries: retry count per chunk on transient errors (rate limits, timeouts).
        - retry_backoff_sec: base backoff seconds (exponential).
        """
        if not text:
            return ""

        if not preserve_format:
            return self._retry_translate(text, retries=retries, backoff=retry_backoff_sec)

        # Preserve format by translating line-by-line in safe chunks
        lines = text.splitlines(keepends=True)
        out: List[str] = []
        for line in lines:
            if not line.strip():
                out.append(line)
                continue
            chunks = self._chunk_text(line, max_chars=max_chars)
            translated_chunks: List[str] = []
            for idx, chunk in enumerate(chunks):
                translated = self._retry_translate(
                    chunk, retries=retries, backoff=retry_backoff_sec
                )
                translated_chunks.append(translated)
            out.append("".join(translated_chunks))
        return "".join(out)

    def translate_file(
        self,
        input_path: str,
        output_path: str,
        *,
        encoding: str = "utf-8",
        preserve_format: bool = True,
        max_chars: int = 4500,
        retries: int = 3,
        retry_backoff_sec: float = 1.0,
    ) -> None:
        """Translate a whole text file and write the result to output_path."""
        with open(input_path, "r", encoding=encoding) as f:
            content = f.read()
        translated = self.translate_text(
            content,
            preserve_format=preserve_format,
            max_chars=max_chars,
            retries=retries,
            retry_backoff_sec=retry_backoff_sec,
        )
        with open(output_path, "w", encoding=encoding) as f:
            f.write(translated)

    @staticmethod
    def en_to_vi(text: str) -> str:
        return GoogleTranslator(source="en", target="vi").translate(text)

    @staticmethod
    def vi_to_en(text: str) -> str:
        return GoogleTranslator(source="vi", target="en").translate(text)

    # ---- internals ----
    def _retry_translate(self, text: str, *, retries: int, backoff: float) -> str:
        attempt = 0
        while True:
            try:
                return self._translator.translate(text)
            except Exception as e:
                attempt += 1
                if attempt > retries:
                    raise e
                time.sleep(backoff * (2 ** (attempt - 1)))

    @staticmethod
    def _chunk_text(text: str, *, max_chars: int = 4500) -> List[str]:
        """Split text into chunks under max_chars at sentence or space boundaries.

        We try to split by sentence terminators first; if still too long, we split by spaces; 
        as a last resort we hard-split.
        """
        if len(text) <= max_chars:
            return [text]

        # First pass: split into sentences while keeping delimiters omitted (we'll re-join)
        sentences = re.split(r"(?<=[\.!?…。！？])\s+", text)
        chunks: List[str] = []
        buf = ""
        for s in sentences:
            s_with_space = (s + " ") if not s.endswith("\n") else s
            if not buf:
                buf = s_with_space
            elif len(buf) + len(s_with_space) <= max_chars:
                buf += s_with_space
            else:
                if buf:
                    chunks.append(buf)
                buf = s_with_space
        if buf:
            chunks.append(buf)

        # If any chunk is still too long, split by spaces
        refined: List[str] = []
        for ch in chunks:
            if len(ch) <= max_chars:
                refined.append(ch)
                continue
            words = ch.split(" ")
            cur = ""
            for w in words:
                seg = (w + " ")
                if not cur:
                    cur = seg
                elif len(cur) + len(seg) <= max_chars:
                    cur += seg
                else:
                    refined.append(cur)
                    cur = seg
            if cur:
                refined.append(cur)

        # Final hard split if still too long
        final: List[str] = []
        for ch in refined:
            if len(ch) <= max_chars:
                final.append(ch)
            else:
                for i in range(0, len(ch), max_chars):
                    final.append(ch[i : i + max_chars])
        return final

    # ---- language utilities ----
    @staticmethod
    def get_supported_languages(as_dict: bool = True) -> Union[Dict[str, str], List[str]]:
        """Return supported languages from GoogleTranslator.

        If as_dict is True, returns mapping name->code per deep-translator's API.
        Otherwise, returns a list of language names.
        """
        # deep-translator exposes language names mapping; keep API consistent
        return GoogleTranslator.get_supported_languages(as_dict=as_dict)

    @staticmethod
    def _normalize_lang(lang: str) -> str:
        """Normalize language input to a code accepted by GoogleTranslator.

        - Accepts language names or codes, case-insensitive.
        - Returns 'auto' unchanged.
        - Attempts to resolve common aliases (e.g., zh-CN vs zh-cn).
        """
        if not lang:
            return "auto"
        if lang.lower() == "auto":
            return "auto"

        # Pull supported mapping name->code from deep-translator
        try:
            mapping = GoogleTranslator.get_supported_languages(as_dict=True)
        except Exception:
            mapping = {}

        # Build search structures
        name_to_code = {str(name).lower(): code for name, code in mapping.items()}
        codes = {str(code).lower(): code for code in mapping.values()}

        key = lang.lower().strip().replace("_", "-")

        # Direct code match (case-insensitive)
        if key in codes:
            return codes[key]

        # Name match (case-insensitive)
        if key in name_to_code:
            return name_to_code[key]

        # Common aliases for Chinese, Portuguese variants, etc.
        alias = {
            "zh-cn": "zh-CN",
            "zh-tw": "zh-TW",
            "pt-br": "pt",
            "pt-pt": "pt",
        }
        if key in alias:
            return alias[key]

        # Fallback: return original (deep-translator may accept) or 'auto'
        return lang

from __future__ import annotations

"""Utilities for tokenizing Japanese text with SudachiPy for word cloud generation."""

from pathlib import Path
from typing import Iterable, List

from sudachipy import dictionary, tokenizer as sudachi_tokenizer

# Initialize Sudachi tokenizer
SUDACHI_MODE = sudachi_tokenizer.Tokenizer.SplitMode.B
_SUDACHI = dictionary.Dictionary().create()

# Load stopwords from bundled file if available
STOPWORDS_PATH = Path(__file__).resolve().parent / "stopwords_ja.txt"
if STOPWORDS_PATH.exists():
    with open(STOPWORDS_PATH, encoding="utf-8") as f:
        STOPWORDS = set(w.strip() for w in f if w.strip())
else:
    STOPWORDS: set[str] = set()


def tokenize_texts(texts: Iterable[str]) -> List[str]:
    """Tokenize ``texts`` using Sudachi and return filtered base-form tokens.

    The tokenizer uses Sudachi's split mode B and keeps only nouns, verbs and
    adjectives. Tokens present in ``STOPWORDS`` are removed.
    """
    tokens: List[str] = []
    for text in texts:
        for m in _SUDACHI.tokenize(text, SUDACHI_MODE):
            if m.part_of_speech()[0] in ["名詞", "動詞", "形容詞"]:
                lemma = m.dictionary_form()
                if lemma and lemma not in STOPWORDS:
                    tokens.append(lemma)
    return tokens

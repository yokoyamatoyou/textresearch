import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MODULE_DIR = os.path.join(BASE_DIR, "coding", "survey_analysis_mvp")
sys.path.insert(0, MODULE_DIR)

from wc_tokenizer import tokenize_texts


def test_tokenize_texts_basic():
    texts = ["美味しいカレーを食べた", "昨日映画を見た", "勉強する"]
    tokens = tokenize_texts(texts)
    assert "カレー" in tokens
    assert "食べる" in tokens
    assert "映画" in tokens
    assert "見る" in tokens
    # stopword 'する' should be removed, but '勉強' should remain
    assert "勉強" in tokens
    assert "する" not in tokens

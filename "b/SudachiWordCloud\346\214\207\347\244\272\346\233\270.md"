# Sudachiを用いたWordCloud生成指示書

## 目的
Sudachiによる形態素解析を活用し、ノイズの少ない高品質な日本語WordCloudを生成する。

## 1. 環境準備
- `sudachipy` と辞書 (`sudachidict_core`) を `requirements.txt` に記載済み。
- 必要に応じて `pip install -r coding/survey_analysis_mvp/requirements.txt` を実行。

## 2. トークン化と前処理
1. Sudachiの分割モードは **B (Middle)** を推奨。
2. 解析結果から **基本形** を取得し、品詞でフィルタリングする。
   - 例: 名詞・動詞・形容詞を採用し、助詞・助動詞などは除外。
3. ストップワードリストを用意し、解析後のトークンから除去する。
   - ユーザー指定の大量ストップワードを `stopwords_ja.txt` などに保存して読み込む。

```python
from sudachipy import tokenizer, dictionary

# Sudachiの設定
mode = tokenizer.Tokenizer.SplitMode.B
sudachi = dictionary.Dictionary().create()

# ストップワード読込
with open('stopwords_ja.txt', encoding='utf-8') as f:
    stopwords = set(w.strip() for w in f)

text = 'ここに解析対象の日本語テキストを入れる'

# 形態素解析
tokens = []
for m in sudachi.tokenize(text, mode):
    if m.part_of_speech()[0] in ['名詞', '動詞', '形容詞']:
        lemma = m.dictionary_form()
        if lemma not in stopwords:
            tokens.append(lemma)

processed_text = ' '.join(tokens)
```

## 3. WordCloud生成
- `wordcloud.WordCloud` を使用。
- フォントには `NotoSansJP` など日本語対応フォントを指定。
- `collocations=False` で隣接語の結合を無効化し、単語頻度を正確に反映。

```python
from wordcloud import WordCloud

wc = WordCloud(
    font_path='coding/survey_analysis_mvp/fonts/NotoSansJP-Regular.otf',
    width=800,
    height=600,
    background_color='white',
    collocations=False
)
wc.generate(processed_text).to_file('output/wordcloud.png')
```

## 4. 品質向上のための追加ヒント
- **ユーザー辞書**を導入し、固有名詞やプロジェクト特有の語を適切に分割。
- **頻度閾値**を設定し、極端に出現回数が少ない語を除外。
- **マスク画像**やカラーマップを利用して視覚的魅力を向上。
- `SudachiPy` の分割モードを切り替えて結果を比較し、最適なモードを選択。

---
この指示書に従い実装することで、ストップワード除去や語形正規化を行った高品質なWordCloudが生成可能となる。

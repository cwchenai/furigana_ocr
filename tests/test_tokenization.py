from types import SimpleNamespace

from furigana_ocr.core.tokenization import Tokenizer


class DummyWord:
    def __init__(self, surface, feature, dictionary_form=None, reading=None):
        self.surface = surface
        self.feature = feature
        if dictionary_form is not None:
            self.dictionary_form = dictionary_form
        if reading is not None:
            self.reading = reading


class DummyTagger:
    def __init__(self, words):
        self._words = words

    def __call__(self, text):  # pragma: no cover - behaviour is deterministic
        return list(self._words)


def test_tokenizer_extracts_readings_from_features():
    tokenizer = Tokenizer()
    words = [
        DummyWord(
            surface="猫",
            feature=["名詞", "普通名詞", "一般", "*", "*", "*", "猫", "ネコ", "ネコ"],
            dictionary_form="猫",
        ),
        DummyWord(
            surface="日本",
            feature="名詞,固有名詞,地域,一般,*,*,日本,ニホン,ニッポン",
            dictionary_form="日本",
        ),
        DummyWord(
            surface="東京",
            feature=SimpleNamespace(reading="トウキョウ"),
            dictionary_form="東京",
        ),
    ]
    tokenizer._tagger = DummyTagger(words)

    tokens = tokenizer.tokenize("猫 日本 東京")

    assert [token.surface for token in tokens] == ["猫", "日本", "東京"]
    assert tokens[0].reading == "ネコ"
    assert tokens[1].reading == "ニホン"
    assert tokens[2].reading == "トウキョウ"

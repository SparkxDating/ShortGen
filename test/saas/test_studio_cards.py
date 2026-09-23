from video_engine.generation_adapter import _card_captions, _wrap_text


def test_card_captions_lead_with_the_topic():
    lines = _card_captions(
        "Ocean facts",
        "The ocean is deep. It covers most of Earth. Salt water is heavy. Fish live there.",
    )
    assert lines[0] == "Ocean facts"
    assert len(lines) == 4
    assert any("Earth" in line for line in lines)


def test_wrap_text_breaks_long_lines():
    class Draw:
        def textlength(self, text, font=None):
            return len(text) * 10

    lines = _wrap_text(Draw(), "one two three four five", font=None, width=90)
    assert lines == ["one two", "three", "four five"]

from orchestration.outcome import classify_outcome, classify_utterance, user_texts_from_history


def test_whole_words_only():
    assert classify_utterance("I know, yesterday was fine") is None
    assert classify_utterance("yes please") == "HOT"
    assert classify_utterance("no thanks") == "COLD"
    assert classify_utterance("I'm interested") == "HOT"


def test_newest_decisive_utterance_wins():
    # newest first: the caller ended on "no", having said "yes" earlier
    assert classify_outcome(["no, stop calling", "yes tell me more"]) == "COLD"
    assert classify_outcome(["yes call me", "no not now"]) == "HOT"


def test_no_signal_is_warm():
    assert classify_outcome(["hmm okay", "let me think"]) == "WARM"
    assert classify_outcome([]) == "WARM"


def test_user_texts_newest_first_from_list_or_json():
    history = [{"user": "first", "ai": "a"}, {"user": "second", "ai": "b"}]
    assert user_texts_from_history(history) == ["second", "first"]
    assert user_texts_from_history('[{"user": "only", "ai": "x"}]') == ["only"]
    assert user_texts_from_history("not json") == []
    assert user_texts_from_history(None) == []


def test_negated_interest_is_a_refusal():
    assert classify_utterance("I am not interested") == "COLD"
    assert classify_utterance("no, not interested, stop calling me") == "COLD"
    assert classify_utterance("I'm really not interested") == "COLD"
    assert classify_utterance("I am not at all interested") == "COLD"
    assert classify_utterance("I'm interested") == "HOT"
    assert classify_utterance("yes, no problem") == "HOT"

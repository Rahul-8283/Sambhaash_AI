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


def test_objection_types():
    from orchestration.objections import classify_objection

    assert classify_objection("that is too expensive") == "price"
    assert classify_objection("is this a scam") == "trust"
    assert classify_objection("I am busy, call me later") == "timing"
    assert classify_objection("not interested") == "not_interested"
    assert classify_objection("hmm") == "other"
    assert classify_objection("") == "other"


def test_bare_refusal_ends_the_call_but_a_discourse_marker_does_not():
    # the live call that regressed: an information request, not a refusal
    assert classify_utterance("No, just tell me what this project is about and what you actually do") is None
    assert classify_utterance("no problem, go on") is None
    assert classify_utterance("I have no questions right now") is None
    # short standalone refusals still end the call
    assert classify_utterance("No.") == "COLD"
    assert classify_utterance("no thanks") == "COLD"
    assert classify_utterance("no, stop calling") == "COLD"
    # a question is never a refusal, however short
    assert classify_utterance("no?") is None


def test_long_refusals_still_caught_by_negated_interest():
    assert classify_utterance("look, I am really not interested in any of this") == "COLD"


def test_discourse_marker_leaves_the_call_warm():
    assert classify_outcome(["No, just tell me what this is about", "hello"]) == "WARM"


def test_do_not_contact_requests_are_detected():
    from orchestration.outcome import classify_utterance, is_do_not_contact

    for text in ("Please don't call me again", "stop calling me", "remove my number from your list",
                 "mujhe call mat karo", "I want to unsubscribe", "Do not disturb me"):
        assert is_do_not_contact(text), text
        assert classify_utterance(text) == "COLD", text


def test_ordinary_sentences_are_not_do_not_contact():
    from orchestration.outcome import is_do_not_contact

    for text in ("Can you call me tomorrow?", "Yes please call me back", "I will call you later", ""):
        assert not is_do_not_contact(text), text

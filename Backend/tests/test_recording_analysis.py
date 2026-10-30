from services.call_recording_service import CallRecordingService


def svc():
    return CallRecordingService.__new__(CallRecordingService)


def test_topics_match_whole_words_only():
    # "button" contains "but", "seed" contains "see": neither is a topic signal
    assert svc()._extract_topics("press the button and plant a seed") == []


def test_topics_found_for_real_words():
    topics = svc()._extract_topics("what is the price, and can I see a demo?")
    assert "pricing" in topics and "demo" in topics


def test_sentiment_ignores_substrings():
    # "goodness" must not count as "good"
    assert svc()._analyze_sentiment("goodness gracious") == "neutral"


def test_sentiment_positive_and_negative():
    assert svc()._analyze_sentiment("That sounds great, thanks") == "positive"
    assert svc()._analyze_sentiment("this is terrible, a real problem") == "negative"

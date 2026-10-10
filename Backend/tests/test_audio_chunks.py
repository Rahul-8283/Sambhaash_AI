"""
The reply is synthesized in chunks and delivered as one <Play> per chunk, so a
turn returns as soon as the chunk that plays first is ready.
"""

import asyncio

import pytest

import api.routes.webhook_routes as wr


@pytest.fixture(autouse=True)
def _clear_cache():
    wr.audio_cache.clear()
    yield
    wr.audio_cache.clear()


def test_finished_chunks_are_served_by_index():
    wr.audio_cache["CA1"] = [b"first", b"second"]
    assert asyncio.run(wr._chunk_bytes("CA1", 0)) == b"first"
    assert asyncio.run(wr._chunk_bytes("CA1", 1)) == b"second"


def test_missing_call_or_index_returns_none():
    assert asyncio.run(wr._chunk_bytes("nope", 0)) is None
    wr.audio_cache["CA1"] = [b"only"]
    assert asyncio.run(wr._chunk_bytes("CA1", 5)) is None


def test_a_pending_chunk_is_awaited_not_skipped():
    async def scenario():
        async def slow():
            await asyncio.sleep(0.05)
            return b"late"

        wr.audio_cache["CA1"] = [b"first", asyncio.create_task(slow())]
        # the words must not be lost just because synthesis was still running
        assert await wr._chunk_bytes("CA1", 1) == b"late"
        # and it is memoized, so a Twilio retry is instant
        assert wr.audio_cache["CA1"][1] == b"late"

    asyncio.run(scenario())


def test_a_failed_chunk_degrades_to_silence():
    async def scenario():
        async def boom():
            raise RuntimeError("sarvam down")

        wr.audio_cache["CA1"] = [b"first", asyncio.create_task(boom())]
        # silence for that chunk beats a 500 that drops the whole call
        assert await wr._chunk_bytes("CA1", 1) is None

    asyncio.run(scenario())


def test_a_chunk_that_never_arrives_times_out(monkeypatch):
    monkeypatch.setattr(wr, "CHUNK_WAIT_SECONDS", 0.05)

    async def scenario():
        async def never():
            await asyncio.sleep(10)

        task = asyncio.create_task(never())
        wr.audio_cache["CA1"] = [b"first", task]
        assert await wr._chunk_bytes("CA1", 1) is None
        task.cancel()

    asyncio.run(scenario())


def test_one_play_tag_per_chunk():
    class FakeClient:
        def build_base_url(self, path):
            return "https://host" + path

    wr.audio_cache["CA1"] = [b"a", b"b", b"c"]
    tags = wr._play_tags(FakeClient(), "CA1")
    assert tags.count("<Play>") == 3
    assert "/audio/CA1/0" in tags and "/audio/CA1/2" in tags
    # order matters: Twilio plays them top to bottom
    assert tags.index("/audio/CA1/0") < tags.index("/audio/CA1/1") < tags.index("/audio/CA1/2")


def test_play_tags_fall_back_to_one_chunk_when_cache_is_empty():
    class FakeClient:
        def build_base_url(self, path):
            return "https://host" + path

    assert wr._play_tags(FakeClient(), "unknown").count("<Play>") == 1


# ---- the real chunking path (FakeTTS in test_call_flow bypasses it) ----

# Splitting needs >=60 chars and >=2 sentences; this is the shape of a real reply.
LONG_REPLY = (
    "Rupeezy is an Indian stock broking platform, and this program lets you earn "
    "commissions by referring clients. Would you like to know more about the structure?"
)


def _manager(fail_texts=()):
    from services.telephony.call_manager import CallManager

    m = CallManager.__new__(CallManager)
    m.synthesized = []

    class FakeFormatter:
        def format_for_twilio(self, data):
            return b"WAV:" + data

    async def synth(text, language):
        m.synthesized.append(text)
        if text in fail_texts:
            raise RuntimeError("sarvam 500")
        return text.encode()

    m.formatter = FakeFormatter()
    m._synthesize = synth
    return m


def test_start_tts_returns_the_first_chunk_and_leaves_the_rest_running():
    from services.telephony.call_manager import split_for_tts

    chunks = split_for_tts(LONG_REPLY)
    assert len(chunks) == 2, "this reply must actually split, or the test proves nothing"

    m = _manager()
    first, pending = asyncio.run(m.start_tts(LONG_REPLY, "en"))

    assert first == b"WAV:" + chunks[0].encode(), "the chunk that plays first is returned"
    assert len(pending) == 1
    assert asyncio.run(_drain(pending)) == [b"WAV:" + chunks[1].encode()]


async def _drain(pending):
    return [await t for t in pending]


def test_short_reply_stays_a_single_chunk():
    m = _manager()
    first, pending = asyncio.run(m.start_tts("Just one sentence.", "en"))
    assert pending == []
    assert first == b"WAV:Just one sentence."


def test_failure_on_the_first_chunk_falls_back_to_one_request():
    from services.telephony.call_manager import split_for_tts

    chunks = split_for_tts(LONG_REPLY)
    m = _manager(fail_texts=(chunks[0],))
    first, pending = asyncio.run(m.start_tts(LONG_REPLY, "en"))

    # the caller must still get playable audio covering the whole reply
    assert first == b"WAV:" + LONG_REPLY.encode()
    assert pending == []
    assert LONG_REPLY in m.synthesized, "fell back to synthesizing the full text"

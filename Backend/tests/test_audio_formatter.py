import io
import math
import struct
import wave

import pytest

from services.tts.audio_formatter import AudioFormatter


def make_wav(rate, channels=1, width=2, seconds=0.5):
    n = int(rate * seconds)
    out = io.BytesIO()
    with wave.open(out, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        frames = b""
        for i in range(n):
            v = int(8000 * math.sin(2 * math.pi * 440 * i / rate))
            for _ in range(channels):
                frames += struct.pack("<h", v) if width == 2 else bytes([(v >> 8) + 128])
        wf.writeframes(frames)
    return out.getvalue()


def info(data):
    with wave.open(io.BytesIO(data), "rb") as wf:
        return wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()


def test_target_format_is_returned_untouched():
    wav = make_wav(8000)
    assert AudioFormatter.format_for_twilio(wav) is wav


@pytest.mark.parametrize("rate", [16000, 22050, 24000, 44100])
def test_resamples_to_8k_with_same_duration(rate):
    ch, width, out_rate, frames = info(AudioFormatter.format_for_twilio(make_wav(rate)))
    assert (ch, width, out_rate) == (1, 2, 8000)
    assert abs(frames - 4000) <= 2


def test_stereo_is_downmixed_to_mono():
    ch, width, rate, _ = info(AudioFormatter.format_for_twilio(make_wav(8000, channels=2)))
    assert (ch, width, rate) == (1, 2, 8000)


def test_8bit_is_widened_to_16bit():
    ch, width, rate, _ = info(AudioFormatter.format_for_twilio(make_wav(8000, width=1)))
    assert (ch, width, rate) == (1, 2, 8000)


def test_empty_and_corrupt_input_raise():
    with pytest.raises(ValueError):
        AudioFormatter.format_for_twilio(b"")
    with pytest.raises(ValueError):
        AudioFormatter.format_for_twilio(b"not a wav file")

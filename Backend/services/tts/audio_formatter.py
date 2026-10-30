import array
import io
import logging
import sys
import wave

logger = logging.getLogger(__name__)

TARGET_RATE = 8000


def _to_mono_16bit(frames: bytes, channels: int, sample_width: int) -> array.array:
    if sample_width == 1:
        samples = array.array("h", ((b - 128) << 8 for b in frames))
    elif sample_width == 2:
        samples = array.array("h")
        samples.frombytes(frames)
        if sys.byteorder == "big":
            samples.byteswap()
    else:
        raise ValueError(f"Unsupported sample width: {sample_width} bytes")

    if channels > 1:
        samples = array.array(
            "h",
            (
                sum(samples[i:i + channels]) // channels
                for i in range(0, len(samples) - channels + 1, channels)
            ),
        )
    return samples


def _resample(samples: array.array, src_rate: int, dst_rate: int) -> array.array:
    if src_rate == dst_rate or not samples:
        return samples
    out_len = max(1, round(len(samples) * dst_rate / src_rate))
    step = src_rate / dst_rate
    last = len(samples) - 1
    out = array.array("h", bytes(2 * out_len))
    for i in range(out_len):
        pos = i * step
        idx = int(pos)
        if idx >= last:
            out[i] = samples[last]
            continue
        frac = pos - idx
        out[i] = int(samples[idx] + (samples[idx + 1] - samples[idx]) * frac)
    return out


class AudioFormatter:
    """
    Formats audio for Twilio telephony: WAV, 8000 Hz, mono, 16-bit PCM.
    Audio already in that format is returned untouched.
    """

    @staticmethod
    def format_for_twilio(raw_audio_bytes: bytes) -> bytes:
        if not raw_audio_bytes:
            logger.error("Received empty audio bytes for formatting.")
            raise ValueError("Audio bytes cannot be empty")

        try:
            with wave.open(io.BytesIO(raw_audio_bytes), "rb") as wf:
                channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                frame_rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
        except wave.Error:
            logger.error("Failed to read audio as WAV. Data might be corrupt.")
            raise ValueError("Invalid or corrupted WAV audio data received")

        if channels == 1 and sample_width == 2 and frame_rate == TARGET_RATE:
            return raw_audio_bytes

        logger.info(
            "Converting audio (%d ch, %d-bit, %d Hz) to 1 ch, 16-bit, %d Hz",
            channels, sample_width * 8, frame_rate, TARGET_RATE,
        )
        samples = _resample(_to_mono_16bit(frames, channels, sample_width), frame_rate, TARGET_RATE)
        if sys.byteorder == "big":
            samples.byteswap()

        out = io.BytesIO()
        with wave.open(out, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(TARGET_RATE)
            wf.writeframes(samples.tobytes())
        return out.getvalue()

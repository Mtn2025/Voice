"""
NumPy-based Audio Utilities (Python 3.13+ Compatible)

Replacement for audioop module with NumPy implementations.
Provides essential audio operations for voice processing.
"""

import numpy as np


def rms(audio_bytes: bytes, width: int = 2) -> int:
    """
    Calculate RMS (Root Mean Square) of audio signal.

    Args:
        audio_bytes: Raw audio data
        width: Bytes per sample (2 for 16-bit)

    Returns:
        RMS value as integer
    """
    if width != 2:
        raise ValueError("Only 16-bit audio (width=2) supported")

    if len(audio_bytes) == 0:
        return 0

    # Convert bytes to int16 array
    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)

    # Calculate RMS
    rms_value = np.sqrt(np.mean(audio_array.astype(np.float64) ** 2))

    return int(rms_value)


def max_amplitude(audio_bytes: bytes, width: int = 2) -> int:
    """
    Find maximum amplitude in audio signal.

    Args:
        audio_bytes: Raw audio data
        width: Bytes per sample (2 for 16-bit)

    Returns:
        Maximum absolute amplitude
    """
    if width != 2:
        raise ValueError("Only 16-bit audio (width=2) supported")

    if len(audio_bytes) == 0:
        return 0

    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    return int(np.max(np.abs(audio_array)))


def mul(audio_bytes: bytes, width: int, factor: float) -> bytes:
    """
    Multiply audio samples by a factor (volume control).

    Args:
        audio_bytes: Raw audio data
        width: Bytes per sample (2 for 16-bit)
        factor: Multiplication factor

    Returns:
        Modified audio as bytes
    """
    if width != 2:
        raise ValueError("Only 16-bit audio (width=2) supported")

    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)

    # Multiply and clip to int16 range
    result = np.clip(audio_array * factor, -32768, 32767).astype(np.int16)

    return result.tobytes()


def add(audio1: bytes, audio2: bytes, width: int) -> bytes:
    """
    Mix two audio signals by adding them.

    Args:
        audio1: First audio signal
        audio2: Second audio signal
        width: Bytes per sample (2 for 16-bit)

    Returns:
        Mixed audio as bytes
    """
    if width != 2:
        raise ValueError("Only 16-bit audio (width=2) supported")

    arr1 = np.frombuffer(audio1, dtype=np.int16)
    arr2 = np.frombuffer(audio2, dtype=np.int16)

    # Pad shorter array with zeros
    if len(arr1) < len(arr2):
        arr1 = np.pad(arr1, (0, len(arr2) - len(arr1)))
    elif len(arr2) < len(arr1):
        arr2 = np.pad(arr2, (0, len(arr1) - len(arr2)))

    # Add and clip
    result = np.clip(arr1.astype(np.int32) + arr2.astype(np.int32), -32768, 32767).astype(np.int16)

    return result.tobytes()


# G.711 A-law and μ-law conversion tables
# Pre-calculated for performance

_ALAW_TO_LINEAR = np.array([
    -5504, -5248, -6016, -5760, -4480, -4224, -4992, -4736,
    -7552, -7296, -8064, -7808, -6528, -6272, -7040, -6784,
    -2752, -2624, -3008, -2880, -2240, -2112, -2496, -2368,
    -3776, -3648, -4032, -3904, -3264, -3136, -3520, -3392,
    -22016, -20992, -24064, -23040, -17920, -16896, -19968, -18944,
    -30208, -29184, -32256, -31232, -26112, -25088, -28160, -27136,
    -11008, -10496, -12032, -11520, -8960, -8448, -9984, -9472,
    -15104, -14592, -16128, -15616, -13056, -12544, -14080, -13568,
    -344, -328, -376, -360, -280, -264, -312, -296,
    -472, -456, -504, -488, -408, -392, -440, -424,
    -88, -72, -120, -104, -24, -8, -56, -40,
    -216, -200, -248, -232, -152, -136, -184, -168,
    -1376, -1312, -1504, -1440, -1120, -1056, -1248, -1184,
    -1888, -1824, -2016, -1952, -1632, -1568, -1760, -1696,
    -688, -656, -752, -720, -560, -528, -624, -592,
    -944, -912, -1008, -976, -816, -784, -880, -848,
    5504, 5248, 6016, 5760, 4480, 4224, 4992, 4736,
    7552, 7296, 8064, 7808, 6528, 6272, 7040, 6784,
    2752, 2624, 3008, 2880, 2240, 2112, 2496, 2368,
    3776, 3648, 4032, 3904, 3264, 3136, 3520, 3392,
    22016, 20992, 24064, 23040, 17920, 16896, 19968, 18944,
    30208, 29184, 32256, 31232, 26112, 25088, 28160, 27136,
    11008, 10496, 12032, 11520, 8960, 8448, 9984, 9472,
    15104, 14592, 16128, 15616, 13056, 12544, 14080, 13568,
    344, 328, 376, 360, 280, 264, 312, 296,
    472, 456, 504, 488, 408, 392, 440, 424,
    88, 72, 120, 104, 24, 8, 56, 40,
    216, 200, 248, 232, 152, 136, 184, 168,
    1376, 1312, 1504, 1440, 1120, 1056, 1248, 1184,
    1888, 1824, 2016, 1952, 1632, 1568, 1760, 1696,
    688, 656, 752, 720, 560, 528, 624, 592,
    944, 912, 1008, 976, 816, 784, 880, 848
], dtype=np.int16)

_ULAW_TO_LINEAR = np.array([
    -32124, -31100, -30076, -29052, -28028, -27004, -25980, -24956,
    -23932, -22908, -21884, -20860, -19836, -18812, -17788, -16764,
    -15996, -15484, -14972, -14460, -13948, -13436, -12924, -12412,
    -11900, -11388, -10876, -10364, -9852, -9340, -8828, -8316,
    -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
    -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
    -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
    -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
    -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
    -1372, -1308, -1244, -1180, -1116, -1052, -988, -924,
    -876, -844, -812, -780, -748, -716, -684, -652,
    -620, -588, -556, -524, -492, -460, -428, -396,
    -372, -356, -340, -324, -308, -292, -276, -260,
    -244, -228, -212, -196, -180, -164, -148, -132,
    -120, -112, -104, -96, -88, -80, -72, -64,
    -56, -48, -40, -32, -24, -16, -8, 0,
    32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
    23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
    15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
    11900, 11388, 10876, 10364, 9852, 9340, 8828, 8316,
    7932, 7676, 7420, 7164, 6908, 6652, 6396, 6140,
    5884, 5628, 5372, 5116, 4860, 4604, 4348, 4092,
    3900, 3772, 3644, 3516, 3388, 3260, 3132, 3004,
    2876, 2748, 2620, 2492, 2364, 2236, 2108, 1980,
    1884, 1820, 1756, 1692, 1628, 1564, 1500, 1436,
    1372, 1308, 1244, 1180, 1116, 1052, 988, 924,
    876, 844, 812, 780, 748, 716, 684, 652,
    620, 588, 556, 524, 492, 460, 428, 396,
    372, 356, 340, 324, 308, 292, 276, 260,
    244, 228, 212, 196, 180, 164, 148, 132,
    120, 112, 104, 96, 88, 80, 72, 64,
    56, 48, 40, 32, 24, 16, 8, 0
], dtype=np.int16)


def alaw2lin(alaw_bytes: bytes, width: int = 2) -> bytes:
    """
    Convert A-law encoded audio to linear PCM.

    Args:
        alaw_bytes: A-law encoded audio
        width: Output width (2 for 16-bit)

    Returns:
        Linear PCM as bytes
    """
    if width != 2:
        raise ValueError("Only 16-bit output (width=2) supported")

    alaw_array = np.frombuffer(alaw_bytes, dtype=np.uint8)
    linear = _ALAW_TO_LINEAR[alaw_array]

    return linear.tobytes()


def ulaw2lin(ulaw_bytes: bytes, width: int = 2) -> bytes:
    """
    Convert μ-law encoded audio to linear PCM.

    Args:
        ulaw_bytes: μ-law encoded audio
        width: Output width (2 for 16-bit)

    Returns:
        Linear PCM as bytes
    """
    if width != 2:
        raise ValueError("Only 16-bit output (width=2) supported")

    ulaw_array = np.frombuffer(ulaw_bytes, dtype=np.uint8)
    linear = _ULAW_TO_LINEAR[ulaw_array]

    return linear.tobytes()


# Linear to A-law/μ-law conversion (reverse lookup)
_LINEAR_TO_ALAW = np.zeros(65536, dtype=np.uint8)
_LINEAR_TO_ULAW = np.zeros(65536, dtype=np.uint8)

# Build reverse lookup tables
for i in range(256):
    linear_val = _ALAW_TO_LINEAR[i]
    # Map signed int16 to unsigned index
    idx = int(linear_val) & 0xFFFF
    _LINEAR_TO_ALAW[idx] = i

for i in range(256):
    linear_val = _ULAW_TO_LINEAR[i]
    idx = int(linear_val) & 0xFFFF
    _LINEAR_TO_ULAW[idx] = i


def lin2alaw(linear_bytes: bytes, width: int = 2) -> bytes:
    """
    Convert linear PCM to A-law encoding.

    Args:
        linear_bytes: Linear PCM audio
        width: Input width (2 for 16-bit)

    Returns:
        A-law encoded audio as bytes
    """
    if width != 2:
        raise ValueError("Only 16-bit input (width=2) supported")

    linear_array = np.frombuffer(linear_bytes, dtype=np.int16)
    # Convert to unsigned indices
    indices = linear_array.view(np.uint16)
    alaw = _LINEAR_TO_ALAW[indices]

    return alaw.tobytes()


def lin2ulaw(linear_bytes: bytes, width: int = 2) -> bytes:
    """
    Convert linear PCM to μ-law encoding.

    Args:
        linear_bytes: Linear PCM audio
        width: Input width (2 for 16-bit)

    Returns:
        μ-law encoded audio as bytes
    """
    if width != 2:
        raise ValueError("Only 16-bit input (width=2) supported")

    linear_array = np.frombuffer(linear_bytes, dtype=np.int16)
    indices = linear_array.view(np.uint16)
    ulaw = _LINEAR_TO_ULAW[indices]

    return ulaw.tobytes()

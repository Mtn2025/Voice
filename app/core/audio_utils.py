"""
Audio Utilities Replacement for audioop (Python 3.13+ compatibility)

This module provides pure Python implementations for audio operations previously
handled by the 'audioop' module, which was removed in Python 3.13.
It focuses on G.711 (A-law/mu-law) conversions and basic 16-bit PCM operations.
Uses pre-calculated Look-Up Tables (LUTs) for efficient G.711 conversion.
"""

import math
import struct

# =============================================================================
# LOOK-UP TABLES GENERATION
# =============================================================================

def _make_decode_tables():
    """Generate G.711 decode tables (8-bit to 16-bit PCM)."""
    # A-law decode table
    tbl_a2p = []
    for i in range(256):
        val = i ^ 0x55
        t = val & 0x7F
        seg = (t & 0x70) >> 4
        x = (t & 0x0F)

        linear_value = (x << 4) + 8 if seg == 0 else (x << 4) + 264 << seg - 1

        if val & 0x80:
            linear_value = -linear_value

        tbl_a2p.append(linear_value)

    # mu-law decode table
    tbl_u2p = []
    for i in range(256):
        val = ~i & 0xFF
        t = ((val & 0x0F) << 3) + 0x84
        seg = (val & 0x70) >> 4
        linear_value = t << seg
        linear_value -= 0x84
        if val & 0x80:
            linear_value = -linear_value
        tbl_u2p.append(linear_value)

    return tbl_a2p, tbl_u2p


def _linear2alaw_sample(pcm_val):
    """Encode single PCM sample to A-law."""
    if pcm_val == -32768:
        pcm_val = -32767

    sign = 0x00
    if pcm_val < 0:
        pcm_val = -pcm_val
        pcm_val = pcm_val - 1
        sign = 0x80

    # Simple Segment-based Encoder for A-law
    if pcm_val < 0:
        pcm_val = -pcm_val
        sign = 0x00  # 0x55 XORed later
    else:
        sign = 0x80

    pcm_val = min(pcm_val, 32767)

    if pcm_val >= 256:
        exp = 7
        for e in range(1, 8):
            if pcm_val < (256 << e):
                exp = e
                break
        mantissa = (pcm_val >> (exp + 3)) & 0x0F
        byte = (exp << 4) | mantissa
    else:
        byte = (pcm_val >> 4)

    encoded = (sign | byte) ^ 0x55
    return encoded


def _linear2ulaw_sample(pcm_val):
    """Encode single PCM sample to mu-law."""
    if pcm_val < 0:
        pcm_val = -pcm_val
        sign = 0x80
    else:
        sign = 0x00

    pcm_val = min(pcm_val, 32635)
    pcm_val += 0x84

    exp = 7
    for e in range(7, -1, -1):
        if (pcm_val & (1 << (e + 3))) != 0:
            exp = e
            break

    mantissa = (pcm_val >> (exp + 3)) & 0x0F
    byte = (sign | (exp << 4) | mantissa)
    return (~byte & 0xFF)


# =============================================================================
# GENERATE TABLES AT MODULE IMPORT
# =============================================================================

# Generate Decode Tables (256 entries each)
_ALAW_TO_PCM, _ULAW_TO_PCM = _make_decode_tables()

# Generate Encode Tables (65536 entries each for full 16-bit range)
_PCM_TO_ALAW = [0] * 65536
_PCM_TO_ULAW = [0] * 65536

for i in range(-32768, 32768):
    _PCM_TO_ALAW[i + 32768] = _linear2alaw_sample(i)
    _PCM_TO_ULAW[i + 32768] = _linear2ulaw_sample(i)


# =============================================================================
# PUBLIC API (audioop compatible)
# =============================================================================

def alaw2lin(fragment: bytes, width: int) -> bytes:
    """
    Convert A-law fragments to linear PCM fragments.

    Args:
        fragment: A-law encoded audio bytes
        width: Destination sample width in bytes (must be 2 for 16-bit)

    Returns:
        Linear PCM bytes
    """
    if width != 2:
        raise ValueError("Only 2-byte (16-bit) width supported for G.711 conversion")

    return b"".join(struct.pack("<h", _ALAW_TO_PCM[b]) for b in fragment)


def ulaw2lin(fragment: bytes, width: int) -> bytes:
    """
    Convert mu-law fragments to linear PCM fragments.

    Args:
        fragment: mu-law encoded audio bytes
        width: Destination sample width in bytes (must be 2 for 16-bit)

    Returns:
        Linear PCM bytes
    """
    if width != 2:
        raise ValueError("Only 2-byte width supported")

    return b"".join(struct.pack("<h", _ULAW_TO_PCM[b]) for b in fragment)


def lin2alaw(fragment: bytes, width: int) -> bytes:
    """
    Convert linear PCM fragments to A-law.

    Args:
        fragment: Linear PCM audio bytes
        width: Source sample width in bytes (must be 2 for 16-bit)

    Returns:
        A-law encoded bytes
    """
    if width != 2:
        raise ValueError("Only 2-byte width supported")

    result = bytearray()
    for i in range(0, len(fragment), 2):
        sample = struct.unpack_from("<h", fragment, i)[0]
        # Clamp to 16-bit range
        sample = max(-32768, min(32767, sample))
        # Map using LUT for speed
        result.append(_PCM_TO_ALAW[sample + 32768])

    return bytes(result)


def lin2ulaw(fragment: bytes, width: int) -> bytes:
    """
    Convert linear PCM fragments to mu-law.

    Args:
        fragment: Linear PCM audio bytes
        width: Source sample width in bytes (must be 2 for 16-bit)

    Returns:
        mu-law encoded bytes
    """
    if width != 2:
        raise ValueError("Only 2-byte width supported")

    result = bytearray()
    for i in range(0, len(fragment), 2):
        sample = struct.unpack_from("<h", fragment, i)[0]
        # Clamp to 16-bit range
        sample = max(-32768, min(32767, sample))
        # Map using LUT for speed
        result.append(_PCM_TO_ULAW[sample + 32768])

    return bytes(result)


def rms(fragment: bytes, width: int) -> int:
    """
    Return the root-mean-square of the fragment.

    Args:
        fragment: PCM audio bytes
        width: Sample width in bytes (must be 2 for 16-bit)

    Returns:
        RMS value as integer
    """
    if width != 2:
        raise ValueError("Only 2-byte width supported")

    if not fragment:
        return 0

    sum_squares = 0.0
    count = len(fragment) // 2
    for i in range(0, len(fragment), 2):
        val = struct.unpack_from("<h", fragment, i)[0]
        sum_squares += val * val

    return int(math.sqrt(sum_squares / count))


def max(fragment: bytes, width: int) -> int:
    """
    Return the maximum peak absolute value of the fragment.

    Args:
        fragment: PCM audio bytes
        width: Sample width in bytes (must be 2 for 16-bit)

    Returns:
        Maximum absolute value as integer
    """
    if width != 2:
        raise ValueError("Only 2-byte width supported")

    max_val = 0
    for i in range(0, len(fragment), 2):
        val = abs(struct.unpack_from("<h", fragment, i)[0])
        max_val = max(val, max_val)

    return max_val


def mul(fragment: bytes, width: int, factor: float) -> bytes:
    """
    Multiply samples by a factor (volume control).

    Args:
        fragment: PCM audio bytes
        width: Sample width in bytes (must be 2 for 16-bit)
        factor: Multiplication factor for volume

    Returns:
        Modified PCM bytes
    """
    if width != 2:
        raise ValueError("Only 2-byte width supported")

    result = bytearray()
    for i in range(0, len(fragment), 2):
        val = struct.unpack_from("<h", fragment, i)[0]
        new_val = int(val * factor)
        # Clip to 16-bit range
        new_val = max(-32768, min(32767, new_val))
        result.extend(struct.pack("<h", new_val))

    return bytes(result)


def add(fragment1: bytes, fragment2: bytes, width: int) -> bytes:
    """
    Return a fragment which is the addition of the two samples.

    Args:
        fragment1: First PCM audio bytes
        fragment2: Second PCM audio bytes
        width: Sample width in bytes (must be 2 for 16-bit)

    Returns:
        Mixed PCM bytes (length of shorter fragment)
    """
    if width != 2:
        raise ValueError("Only 2-byte width supported")

    min_len = min(len(fragment1), len(fragment2))
    result = bytearray()

    for i in range(0, min_len, 2):
        val1 = struct.unpack_from("<h", fragment1, i)[0]
        val2 = struct.unpack_from("<h", fragment2, i)[0]
        new_val = val1 + val2
        # Clip to 16-bit range
        new_val = max(-32768, min(32767, new_val))
        result.extend(struct.pack("<h", new_val))

    return bytes(result)

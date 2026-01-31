import numpy as np


class AudioProcessor:
    """
    Modern replacement for 'audioop' using NumPy.
    Provides G.711 (u-law/A-law) codecs and PCM manipulation.
    Optimized for 16-bit PCM (width=2) and 8-bit G.711.
    """

    # Pre-compute LUTs at import time for speed
    _ulaw_to_lin_table = None
    _alaw_to_lin_table = None
    _lin_to_ulaw_table = None
    _lin_to_alaw_table = None

    @classmethod
    def _init_tables(cls):
        """Initializes G.711 Lookup Tables using vectorized NumPy operations."""
        if cls._ulaw_to_lin_table is not None:
            return

        # --- U-LAW DECODE (8-bit -> 16-bit) ---
        # Standard G.711 u-law expansion
        # NOTE: Incomplete implementation - using lookup table approach
        # Standard expansion formula: sgn(m) * (1/255) * ((1+mu)^|m| - 1) * max_amplitude

        # Create expansion table
        table_ulaw = np.zeros(256, dtype=np.int16)
        for i in range(256):
            ulawbyte = ~i & 0xFF # Invert bits first
            sign = (ulawbyte & 0x80)
            exponent = (ulawbyte >> 4) & 0x07
            mantissa = (ulawbyte & 0x0F)
            sample = ((mantissa << 3) + 0x84) << exponent
            sample -= 0x84
            if sign != 0:
                sample = -sample
            table_ulaw[i] = sample
        cls._ulaw_to_lin_table = table_ulaw

        # --- A-LAW DECODE (8-bit -> 16-bit) ---
        table_alaw = np.zeros(256, dtype=np.int16)
        for i in range(256):
            alawbyte = i ^ 0x55
            sign = (alawbyte & 0x80)
            exponent = (alawbyte >> 4) & 0x07
            mantissa = (alawbyte & 0x0F)
            sample = (mantissa << 4) + 8 if exponent == 0 else (mantissa << 4) + 264 << exponent - 1
            if sign == 0:
                sample = -sample
            table_alaw[i] = sample
        cls._alaw_to_lin_table = table_alaw

    @classmethod
    def _ensure_init(cls):
        if cls._ulaw_to_lin_table is None:
            cls._init_tables()

    @staticmethod
    def rms(fragment: bytes, width: int) -> int:
        """Returns the Root Mean Square of the audio fragment."""
        if len(fragment) == 0:
            return 0
        try:
            dtype = np.int16 if width == 2 else np.int8
            # frombuffer is instant (no copy)
            data = np.frombuffer(fragment, dtype=dtype)
            # Calculate RMS: sqrt(mean(x^2))
            # Cast to float64 to avoid overflow during square
            squares = data.astype(np.float64) ** 2
            mean = np.mean(squares)
            return int(np.sqrt(mean))
        except Exception:
            return 0

    @staticmethod
    def max_val(fragment: bytes, width: int) -> int:
        """Returns the maximum absolute value in the fragment."""
        if len(fragment) == 0:
            return 0
        dtype = np.int16 if width == 2 else np.int8
        data = np.frombuffer(fragment, dtype=dtype)
        # Use abs().max()
        return int(np.max(np.abs(data))) if data.size > 0 else 0

    @classmethod
    def ulaw2lin(cls, fragment: bytes, width: int) -> bytes:
        """Converts u-law fragment to linear PCM."""
        cls._ensure_init()
        # Input is uint8, Output is int16
        indices = np.frombuffer(fragment, dtype=np.uint8)
        # Fast LUT lookup
        pcm = cls._ulaw_to_lin_table[indices]
        return pcm.tobytes()

    @classmethod
    def alaw2lin(cls, fragment: bytes, width: int) -> bytes:
        """Converts A-law fragment to linear PCM."""
        cls._ensure_init()
        indices = np.frombuffer(fragment, dtype=np.uint8)
        pcm = cls._alaw_to_lin_table[indices]
        return pcm.tobytes()

    @staticmethod
    def lin2ulaw(fragment: bytes, width: int) -> bytes:
        """Converts linear PCM to u-law."""
        # For encoding, the algorithm is complex to vectorize perfectly with bit manipulation
        # without C-level speed, but NumPy logic is fast enough for chunks.
        # Implements G.711 u-law compression.

        dtype = np.int16 if width == 2 else np.int8
        pcm = np.frombuffer(fragment, dtype=dtype)

        # Bias
        BIAS = 0x84  # noqa: N806 - Algorithm constant
        CLIP = 32635  # noqa: N806 - Algorithm constant

        # Process: clip -> absolute value -> bias
        pcm = np.abs(pcm)  # Get absolute value (sign will be encoded in output)

        # 2. Clipping
        pcm = np.minimum(pcm, CLIP)

        # 3. Bias
        pcm = pcm + BIAS

        # 4. Exponent
        # Fast way to find exponent?
        # We can loosely estimate using log2 or conditionals.
        # Standard map:
        # Exponent 0: < 0x100 (256) (actually we added bias 132... so range starts higher)
        # Let's use a simpler vectorized logic if possible.

        # Given strict G.711 is tricky to vectorize concisely in pure py-numpy without loops or lookups,
        # we will use a "Quantization Table" approach which is standard.
        # But mapping 65536 values to 256 is a big LUT (64KB).
        # Actually 64KB is tiny for modern RAM. Generating the Encoding LUT is the best way.

        if not hasattr(AudioProcessor, '_lin_to_ulaw_lut'):
             AudioProcessor._lin_to_ulaw_lut = AudioProcessor._generate_lin2ulaw_lut()

        # Offset PCM to 0..65535 for array indexing (since it's signed int16)
        # pcm values are -32768 to 32767.
        # We need to cast inputs to uint16 index: (val + 32768)
        indices = (np.frombuffer(fragment, dtype=np.int16).astype(np.int32) + 32768)
        return AudioProcessor._lin_to_ulaw_lut[indices].tobytes()

    @staticmethod
    def lin2alaw(fragment: bytes, width: int) -> bytes:
        if not hasattr(AudioProcessor, '_lin_to_alaw_lut'):
             AudioProcessor._lin_to_alaw_lut = AudioProcessor._generate_lin2alaw_lut()

        indices = (np.frombuffer(fragment, dtype=np.int16).astype(np.int32) + 32768)
        return AudioProcessor._lin_to_alaw_lut[indices].tobytes()

    @staticmethod
    def _generate_lin2ulaw_lut():
        """Generates a 64KB LUT for Int16 -> U-Law conversion."""
        # This runs once at startup.
        lut = np.zeros(65536, dtype=np.uint8)
        # Iterate native python for clarity in generation, it's 65k loops, < 50ms.
        for i in range(65536):
            pcm_val = i - 32768
            # Encode logic
            sign = 0x80 if pcm_val < 0 else 0
            pcm_val = abs(pcm_val)
            pcm_val = min(pcm_val, 32635)
            pcm_val += 0x84
            exponent = 7
            for exp in range(7, -1, -1):
                if pcm_val & (1 << (exp + 3)):
                    exponent = exp
                    break
            mantissa = (pcm_val >> (exponent + 3)) & 0x0F
            byte = ~(sign | (exponent << 4) | mantissa)
            lut[i] = byte & 0xFF
        return lut

    @staticmethod
    def _generate_lin2alaw_lut():
         """Generates a 64KB LUT for Int16 -> A-Law conversion."""
         lut = np.zeros(65536, dtype=np.uint8)
         for i in range(65536):
             pcm_val = i - 32768
             sign = 0x00 if pcm_val < 0 else 0x80 # Note: A-law sign bit convention varies, using standard
             # Note: standard A-law: even bits inverted.
             pcm_val = abs(pcm_val)
             pcm_val = min(pcm_val, 32635)

             if pcm_val >= 256:
                 exponent = 7
                 for exp in range(7, -1, -1):
                     if pcm_val & (1 << (exp + 4)):
                         exponent = exp
                         break
                 mantissa = (pcm_val >> (exponent + 4)) & 0x0F
             else:
                 exponent = 0
                 mantissa = (pcm_val >> 4) & 0x0F

             byte = (sign | (exponent << 4) | mantissa) ^ 0x55
             lut[i] = byte & 0xFF
         return lut

    @staticmethod
    def mul(fragment: bytes, width: int, factor: float) -> bytes:
        """Multiplies amplitude by factor."""
        if len(fragment) == 0:
            return b""
        dtype = np.int16 if width == 2 else np.int8
        data = np.frombuffer(fragment, dtype=dtype)
        # Multiply and cast
        multiplied = np.clip(data * factor, -32768, 32767).astype(dtype)
        return multiplied.tobytes()

    @staticmethod
    def add(fragment1: bytes, fragment2: bytes, width: int) -> bytes:
        """Adds two audio fragments directly."""
        dtype = np.int16 if width == 2 else np.int8
        d1 = np.frombuffer(fragment1, dtype=dtype)
        d2 = np.frombuffer(fragment2, dtype=dtype)

        # Pad to match lengths logic? audioop crashes or truncates?
        # audioop truncates to shortest.
        min_len = min(len(d1), len(d2))
        d1 = d1[:min_len]
        d2 = d2[:min_len]

        # Add with Clipping to prevent overflow wrap-around
        # Cast to int32 for addition, then clip
        added = np.clip(d1.astype(np.int32) + d2.astype(np.int32), -32768, 32767).astype(dtype)
        return added.tobytes()

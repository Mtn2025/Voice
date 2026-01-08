"""
Tests unitarios para AdaptiveInputFilter (VAD).

NOTA: Estos tests requieren el módulo 'audioop' que fue removido en Python 3.13.
Si audioop no está disponible, los tests se saltarán automáticamente.
"""

# Verificar si audioop está disponible
import importlib.util

import pytest

from app.core.vad_filter import AdaptiveInputFilter

AUDIOOP_AVAILABLE = importlib.util.find_spec("audioop") is not None or importlib.util.find_spec("audioop_lts") is not None


@pytest.mark.unit
@pytest.mark.skipif(not AUDIOOP_AVAILABLE, reason="audioop module not available (Python 3.13+)")
class TestAdaptiveInputFilter:
    """Suite de tests para filtro VAD adaptativo."""

    def test_initialization(self):
        """Test: El filtro se inicializa correctamente."""
        filter = AdaptiveInputFilter()

        assert filter.samples == 0
        assert filter.avg_rms == 0.0
        assert filter.min_rms == 1.0
        assert filter.max_rms == 0.0
        assert filter.ready is False

    def test_update_profile_single_sample(self):
        """Test: Una muestra actualiza pero no activa el filtro."""
        filter = AdaptiveInputFilter()

        filter.update_profile(0.5)

        assert filter.samples == 1
        assert filter.avg_rms == 0.5
        assert filter.ready is False  # Requiere >= 5 samples

    def test_update_profile_calibration(self):
        """Test: 5 muestras activan el filtro (calibración completa)."""
        filter = AdaptiveInputFilter()

        # Simular 5 muestras
        for i in range(5):
            filter.update_profile(0.1 * (i + 1))  # 0.1, 0.2, 0.3, 0.4, 0.5

        assert filter.samples == 5
        assert filter.ready is True
        assert filter.avg_rms > 0  # Debe tener promedio calculado

    def test_should_filter_low_rms(self):
        """Test: RMS bajo debe ser filtrado (ruido)."""
        filter = AdaptiveInputFilter()

        # Calibrar con valores altos
        for _i in range(5):
            filter.update_profile(0.8)

        # RMS muy bajo comparado con calibración
        should_filter = filter.should_filter(0.05, silence_detected=False)

        assert should_filter is True  # Debe filtrar ruido bajo

    def test_should_filter_high_rms(self):
        """Test: RMS alto NO debe ser filtrado (voz)."""
        filter = AdaptiveInputFilter()

        # Calibrar con valores normales
        for _i in range(5):
            filter.update_profile(0.3)

        # RMS alto indica voz
        should_filter = filter.should_filter(0.5, silence_detected=False)

        assert should_filter is False  # NO filtrar voz

    def test_should_filter_silence_detected(self):
        """Test: Si Azure detecta silencio, filtrar independientemente de RMS."""
        filter = AdaptiveInputFilter()

        # Calibrar
        for _i in range(5):
            filter.update_profile(0.3)

        # Silence detected overrides RMS check
        should_filter = filter.should_filter(0.9, silence_detected=True)

        assert should_filter is True

    def test_min_max_rms_tracking(self):
        """Test: El filtro rastrea min/max RMS correctamente."""
        filter = AdaptiveInputFilter()

        filter.update_profile(0.1)  # Min
        filter.update_profile(0.9)  # Max
        filter.update_profile(0.5)

        assert filter.min_rms <= 0.1
        assert filter.max_rms >= 0.9

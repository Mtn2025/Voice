"""
Test completo de integración para controles de Voz/TTS (Fase II).
Verifica: DB persistence + 3-profile independence.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import AgentConfig

print("🧪 TEST: TTS Controls Integration\n")
print("=" * 80)

# Create engine
engine = create_engine('sqlite:///asistente.db')
Session = sessionmaker(bind=engine)
session = Session()

# ============================================================================
# TEST 1: Database Persistence (CRUD)
# ============================================================================
print("\n📝 TEST 1: Database Persistence")
print("-" * 80)

# Create test config
test_config = AgentConfig(
    name="test_tts_controls_v2",
    
    # Browser Profile (11Labs Strict)
    voice_stability=0.3,
    voice_similarity_boost=0.8,
    voice_speaker_boost=True,
    voice_filler_injection=True,
    tts_output_format="mp3_44100_128",
    
    # Twilio Profile (Phone Optimized)
    voice_stability_phone=0.6, 
    voice_similarity_boost_phone=0.5, # Lower for speed
    voice_speaker_boost_phone=False,
    voice_filler_injection_phone=False,
    tts_output_format_phone="pcm_8000",
    
    # Telnyx Profile (High Res)
    voice_stability_telnyx=0.4,
    voice_similarity_boost_telnyx=0.9,
    voice_speaker_boost_telnyx=True,
    voice_filler_injection_telnyx=True,
    tts_output_format_telnyx="ulaw_8000",
)

# Save to DB
session.add(test_config)
session.commit()
config_id = test_config.id
print(f"✅ CREATED: Config ID {config_id}")

# Read back
loaded_config = session.query(AgentConfig).filter_by(id=config_id).first()

# Verify Browser
assert loaded_config.voice_stability == 0.3, "Browser Stability mismatch"
assert loaded_config.voice_similarity_boost == 0.8, "Browser Similarity mismatch"
assert loaded_config.voice_speaker_boost == True, "Browser SpeakerBoost mismatch"
assert loaded_config.voice_filler_injection == True, "Browser Filler mismatch"
assert loaded_config.tts_output_format == "mp3_44100_128", "Browser Format mismatch"
print("✅ BROWSER PROFILE: Fields match")

# Verify Twilio
assert loaded_config.voice_stability_phone == 0.6, "Twilio Stability mismatch"
assert loaded_config.voice_similarity_boost_phone == 0.5, "Twilio Similarity mismatch"
assert loaded_config.voice_speaker_boost_phone == False, "Twilio SpeakerBoost mismatch"
assert loaded_config.voice_filler_injection_phone == False, "Twilio Filler mismatch"
assert loaded_config.tts_output_format_phone == "pcm_8000", "Twilio Format mismatch"
print("✅ TWILIO PROFILE: Fields match")

# Verify Telnyx
assert loaded_config.voice_stability_telnyx == 0.4, "Telnyx Stability mismatch"
assert loaded_config.voice_similarity_boost_telnyx == 0.9, "Telnyx Similarity mismatch"
assert loaded_config.voice_speaker_boost_telnyx == True, "Telnyx SpeakerBoost mismatch"
assert loaded_config.voice_filler_injection_telnyx == True, "Telnyx Filler mismatch"
assert loaded_config.tts_output_format_telnyx == "ulaw_8000", "Telnyx Format mismatch"
print("✅ TELNYX PROFILE: Fields match")

print("\n🎉 TEST 1 PASSED: 15+ new TTS fields persist correctly")

# ============================================================================
# TEST 2: Conditional Logic Verification (Simulated)
# ============================================================================
print("\n📝 TEST 2: 3-Profile Independence")
print("-" * 80)

assert loaded_config.voice_stability != loaded_config.voice_stability_phone, "Profiles not independent"
assert loaded_config.tts_output_format != loaded_config.tts_output_format_phone, "Formats not independent"

print("✅ Independence Confirmed")

# ============================================================================
# CLEANUP
# ============================================================================
session.delete(test_config)
session.commit()
session.close()

print("\n" + "=" * 80)
print("🎉 ALL TESTS PASSED!")
print("=" * 80)
print("✅ Database Persistence: OK")
print("✅ 3-Profile Independence: OK")
print("\n🚀 TTS Controls Implementation: READY FOR PRODUCTION UI")

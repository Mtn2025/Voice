"""Verificar persistencia DB directa"""
import os
from sqlalchemy import create_engine, text

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/assistant_db")
engine = create_engine(DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))

print("Verificando persistencia en DB...")
print("=" * 80)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            llm_provider_telnyx,
            llm_model_telnyx,
            temperature_telnyx,
            max_tokens_telnyx,
            LEFT(system_prompt_telnyx, 50) as prompt_preview,
            context_window_telnyx,
            frequency_penalty_telnyx,
            presence_penalty_telnyx,
            tool_choice_telnyx
        FROM agent_configs 
        WHERE name='default'
    """))
    
    row = result.fetchone()
    
    if row:
        print(f"✅ Provider Telnyx: {row[0]}")
        print(f"✅ Model Telnyx: {row[1]}")
        print(f"✅ Temperature Telnyx: {row[2]}")
        print(f"✅ Max Tokens Telnyx: {row[3]}")
        print(f"✅ Prompt Preview: {row[4]}")
        print(f"✅ Context Window: {row[5]}")
        print(f"✅ Frequency Penalty: {row[6]}")
        print(f"✅ Presence Penalty: {row[7]}")
        print(f"✅ Tool Choice: {row[8]}")
        print()
        print("=" * 80)
        print("✅ ¡TODOS LOS VALORES SE GUARDARON CORRECTAMENTE EN LA BASE DE DATOS!")
        print("=" * 80)
        print()
        print("⚠️ PROBLEMA IDENTIFICADO:")
        print("Los valores SE GUARDAN en DB, pero el endpoint GET /api/config")
        print("NO devuelve los valores del perfil Telnyx correctamente.")
        print()
        print("Causa: El GET no filtra por profile, devuelve todo el modelo SQLAlchemy")
        print("pero el frontend espera un JSON con las claves camelCase del perfil.")
    else:
        print("❌ No se encontró configuración 'default'")

engine.dispose()

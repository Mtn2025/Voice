"""
Create all database tables from SQLAlchemy models including new LLM controls.
"""
from app.db.models import Base
from sqlalchemy import create_engine, inspect

# Create SQLite engine
engine = create_engine('sqlite:///asistente.db', echo=True)

print("🗄️  Creating all tables from models.py...\n")

# Create all tables
Base.metadata.create_all(bind=engine)

print("\n✅ Tables created successfully!\n")

# Verify agent_configs schema
inspector = inspect(engine)
columns = inspector.get_columns('agent_configs')

print(f"📊 Agent Configs table has {len(columns)} columns:\n")

# Find LLM control columns
llm_controls = [
    col['name'] for col in columns 
    if any(prefix in col['name'] for prefix in [
        'context_window', 'frequency_penalty', 'presence_penalty', 
        'tool_choice', 'dynamic_vars'
    ])
]

print(f"🧠 LLM Control Fields ({len(llm_controls)}/18):")
for col in sorted(llm_controls):
    print(f"   ✅ {col}")

if len(llm_controls) == 18:
    print("\n🎉 ALL 18 LLM CONTROL FIELDS PRESENT!")
else:
    print(f"\n⚠️  Expected 18, found {len(llm_controls)}")

print(f"\n✅ Database ready for testing!")

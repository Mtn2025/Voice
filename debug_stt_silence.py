from app.routers.dashboard import FIELD_ALIASES
from app.db.models import AgentConfig

key = 'sttSilenceTimeout'
normalized = FIELD_ALIASES.get(key, key)
suffix = '_telnyx'
db_column = f'{normalized}{suffix}'

print(f'Frontend key: {key}')
print(f'Normalized (from FIELD_ALIASES): {normalized}')
print(f'DB Column (normalized + suffix): {db_column}')
print(f'Has attr on AgentConfig model: {hasattr(AgentConfig, db_column)}')
print(f'All stt_silence attrs: {[a for a in dir(AgentConfig) if "stt_silence" in a]}')

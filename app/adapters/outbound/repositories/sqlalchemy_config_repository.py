"""
SQLAlchemy Config Repository Adapter (Hexagonal Architecture).

Implements ConfigRepositoryPort for database persistence.
Translates domain calls to SQLAlchemy ORM queries.
"""

from app.db.models import AgentConfig
from app.domain.ports.config_repository_port import ConfigDTO, ConfigRepositoryPort
from app.services.db_service import db_service


class SQLAlchemyConfigRepository(ConfigRepositoryPort):
    """
    Adapter for config persistence implementing ConfigRepositoryPort using SQLAlchemy.
    """

    def __init__(self, session_factory):
        """
        Initialize repository with session factory.

        Args:
            session_factory: Callable that returns AsyncSession
        """
        self._session_factory = session_factory

    async def get_config(self, profile: str = "default") -> ConfigDTO:
        """
        Get config by profile (Implementation of Port).
        Currently maps Agent ID 1 to 'default' profile.
        """
        async with self._session_factory() as session:
            # Current Implementation: Single Agent (ID=1)
            orm_config = await db_service.get_agent_config(session)
            if not orm_config:
                from app.domain.ports.config_repository_port import ConfigNotFoundException
                raise ConfigNotFoundException(f"Profile {profile} not found")
            return self._to_dto(orm_config)

    async def update_config(self, profile: str, **updates) -> ConfigDTO:
        """Update config (Implementation of Port)."""
        async with self._session_factory() as session:
             orm_config = await db_service.get_agent_config(session)
             if not orm_config:
                 from app.domain.ports.config_repository_port import ConfigNotFoundException
                 raise ConfigNotFoundException(f"Profile {profile} not found")

             # Apply updates to ORM
             for key, value in updates.items():
                 if hasattr(orm_config, key):
                     setattr(orm_config, key, value)

             session.add(orm_config)
             await session.commit()
             await session.refresh(orm_config)
             return self._to_dto(orm_config)

    async def create_config(self, profile: str, config: ConfigDTO) -> ConfigDTO:
        """Create config (Implementation of Port)."""
        # Placeholder for full implementation if dynamic agent creation is added
        return config

    def _to_dto(self, orm_model) -> ConfigDTO:
        """Helper to convert ORM model to ConfigDTO."""
        return ConfigDTO(
            llm_provider=orm_model.llm_provider or "groq",
            llm_model=orm_model.llm_model or "llama-3.3-70b-versatile",
            tts_provider=orm_model.tts_provider or "azure",
            stt_provider=orm_model.stt_provider or "azure",
        )

    # ... Legacy methods below (maintained for backward compatibility) ...

    async def get_agent_config(self, agent_id: int) -> AgentConfig | None:
        """
        Get agent configuration by ID.
        """
        async with self._session_factory() as session:
            return await db_service.get_agent_config(session)

    async def save_agent_config(self, config: AgentConfig) -> AgentConfig:
        """
        Save agent configuration.
        """
        async with self._session_factory() as session:
            session.add(config)
            await session.commit()
            await session.refresh(config)
            return config

    async def delete_agent_config(self, agent_id: int) -> bool:
        """
        Delete agent configuration.
        """
        async with self._session_factory() as session:
            config = await db_service.get_agent_config(session, agent_id)
            if config:
                await session.delete(config)
                await session.commit()
                return True
            return False

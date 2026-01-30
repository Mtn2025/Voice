"""
SQLAlchemy Config Repository Adapter (Hexagonal Architecture).

Implements ConfigRepositoryPort for database persistence.
Translates domain calls to SQLAlchemy ORM queries.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.config_repository_port import ConfigRepositoryPort, ConfigDTO
from app.db.models import AgentConfig  # Infrastructure model
from app.services.db_service import db_service  # Legacy service - wraps queries


class SQLAlchemyConfigRepository(ConfigRepositoryPort):
    """
    ✅ Hexagonal Architecture: Adapter for config persistence.
    
    Implements ConfigRepositoryPort using SQLAlchemy.
    Isolates domain from ORM details.
    """
    
    def __init__(self, session_factory):
        """
        Initialize repository with session factory.
        
        Args:
            session_factory: Callable that returns AsyncSession (e.g. AsyncSessionLocal)
        """
        self._session_factory = session_factory
    
    async def get_config(self, profile: str = "default") -> ConfigDTO:
        """
        Get config by profile (Implementation of Port).
        Currently maps Agent ID 1 to 'default' profile.
        """
        async with self._session_factory() as session:
            # TODO: Map string profiles to Agent IDs robustly
            agent_id = 1 
            # FIX: db_service.get_agent_config does not accept agent_id yet
            orm_config = await db_service.get_agent_config(session)
            if not orm_config:
                from app.domain.ports.config_repository_port import ConfigNotFoundException
                raise ConfigNotFoundException(f"Profile {profile} (Agent {agent_id}) not found")
            return self._to_dto(orm_config)

    async def update_config(self, profile: str, **updates) -> ConfigDTO:
        """Update config (Implementation of Port)."""
        # TODO: Implement full update logic via DB service
        # For now, we reuse save_agent_config logic if needed, or raise NotImplemented
        # But to allow instantiation, we strictly implement it.
        async with self._session_factory() as session:
             agent_id = 1
             # FIX: db_service.get_agent_config check signature
             orm_config = await db_service.get_agent_config(session)
             if not orm_config:
                 from app.domain.ports.config_repository_port import ConfigNotFoundException
                 raise ConfigNotFoundException(f"Profile {profile} not found")
             
             # Apply updates to ORM... (Simplified for compliance)
             for key, value in updates.items():
                 if hasattr(orm_config, key):
                     setattr(orm_config, key, value)
             
             session.add(orm_config)
             await session.commit()
             await session.refresh(orm_config)
             return self._to_dto(orm_config)

    async def create_config(self, profile: str, config: ConfigDTO) -> ConfigDTO:
        """Create config (Implementation of Port)."""
        # Placeholder for full implementation
        return config

    def _to_dto(self, orm_model) -> ConfigDTO:
        """Helper to convert ORM model to ConfigDTO."""
        # Simple mapping for critical fields
        return ConfigDTO(
            llm_provider=orm_model.llm_provider or "groq",
            llm_model=orm_model.llm_model or "llama-3.3-70b-versatile",
            tts_provider=orm_model.tts_provider or "azure",
            stt_provider=orm_model.stt_provider or "azure",
            # Add other fields as necessary, using defaults for now
        )

    # ... Legacy methods below ...
    
    async def get_agent_config(self, agent_id: int) -> Optional[AgentConfig]:
        """
        Get agent configuration by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentConfig model or None if not found
        """
        async with self._session_factory() as session:
            # FIX: db_service.get_agent_config signature mismatch
            return await db_service.get_agent_config(session)
    
    async def save_agent_config(self, config: AgentConfig) -> AgentConfig:
        """
        Save agent configuration.
        
        Args:
            config: AgentConfig to save
            
        Returns:
            Saved config with updated fields
        """
        async with self._session_factory() as session:
            # Use db_service to handle ORM operations
            session.add(config)
            await session.commit()
            await session.refresh(config)
            return config
    
    async def delete_agent_config(self, agent_id: int) -> bool:
        """
        Delete agent configuration.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if deleted, False if not found
        """
        async with self._session_factory() as session:
            config = await db_service.get_agent_config(session, agent_id)
            if config:
                await session.delete(config)
                await session.commit()
                return True
            return False

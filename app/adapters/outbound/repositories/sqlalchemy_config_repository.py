"""
SQLAlchemy Config Repository Adapter (Hexagonal Architecture).

Implements ConfigRepositoryPort for database persistence.
Translates domain calls to SQLAlchemy ORM queries.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.config_repository_port import ConfigRepositoryPort
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
    
    async def get_agent_config(self, agent_id: int) -> Optional[AgentConfig]:
        """
        Get agent configuration by ID.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentConfig model or None if not found
        """
        async with self._session_factory() as session:
            return await db_service.get_agent_config(session, agent_id)
    
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

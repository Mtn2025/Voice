"""
Factory function for get_call_repository.
"""

from app.domain.ports import CallRepositoryPort


def get_call_repository() -> CallRepositoryPort:
    """
    Factory for CallRepositoryPort.
    
    ✅ FIX VIOLATION #1: Provides CallRepositoryPort from DI container.
    
    Returns:
        Instance of CallRepositoryPort (SQLAlchemyCallRepository)
    """
    from app.infrastructure.di_container import container
    return container.call_repository()

"""
History Router - Call History Management.

Handles all call history endpoints (list, delete, clear).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_simple import verify_api_key
from app.db.database import get_db
from app.db.models import Call

logger = logging.getLogger(__name__)
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(
    prefix="/api/history",
    tags=["history"],
    dependencies=[Depends(verify_api_key)]
)


@router.get("/rows", response_class=HTMLResponse)
async def history_rows(
    request: Request,
    page: int = 1,
    limit: int = 20,
    client_type: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch paginated call history rows with optional filtering.
    """
    try:
        offset = (page - 1) * limit
        query = select(Call).order_by(Call.created_at.desc())

        # Filter by client_type if provided and not 'all'
        if client_type and client_type.lower() != 'all':
            query = query.where(Call.client_type == client_type)

        # Execute query with pagination
        # Note: We need a better way to count total with filters, but for now simple query
        result = await db.execute(query.limit(limit).offset(offset))
        calls = result.scalars().all()

        # Get total count (filtered)
        count_query = select(func.count(Call.id))
        if client_type and client_type.lower() != 'all':
            count_query = count_query.where(Call.client_type == client_type)

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return templates.TemplateResponse(
            "partials/history_rows.html",
            {
                "request": request,
                "calls": calls,
                "total": total,
                "page": page,
                "current_filter": client_type or 'all'
            }
        )

    except Exception as e:
        logger.error(f"❌ Failed to fetch history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history") from e


@router.post("/delete-selected")
async def delete_selected(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Delete selected call records by IDs.
    Expects JSON: {"ids": [1, 2, 3]}
    """
    try:
        body = await request.json()
        ids = body.get("ids", [])

        if not ids:
            return {"status": "ok", "deleted": 0}

        result = await db.execute(
            delete(Call).where(Call.id.in_(ids))
        )
        await db.commit()

        deleted_count = result.rowcount
        logger.info(f"✅ Deleted {deleted_count} call records")

        return {"status": "ok", "deleted": deleted_count}

    except Exception as e:
        logger.error(f"❌ Delete selected failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/clear")
async def clear_history(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Clear entire call history.
    WARNING: Deletes all records permanently.
    """
    try:
        result = await db.execute(delete(Call))
        await db.commit()

        deleted_count = result.rowcount
        logger.info(f"✅ Cleared history: {deleted_count} records deleted")

        return {"status": "ok", "deleted": deleted_count}

    except Exception as e:
        logger.error(f"❌ Clear history failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e)) from e

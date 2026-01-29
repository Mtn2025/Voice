"""
History Router - Call History Management

Extracted from dashboard.py for clean architecture.
Handles all call history endpoints (list, delete, clear).
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, delete
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
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch paginated call history rows.
    Returns HTML table rows for AJAX loading.
    """
    try:
        offset = (page - 1) * limit
        
        # Query calls with pagination
        result = await db.execute(
            select(Call)
            .order_by(Call.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        calls = result.scalars().all()
        
        # Get total count
        count_result = await db.execute(select(func.count(Call.id)))
        total = count_result.scalar()
        
        return templates.TemplateResponse(
            "partials/history_rows.html",
            {
                "request": request,
                "calls": calls,
                "total": total,
                "page": page
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to fetch history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")


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
        
        # Delete calls
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
        raise HTTPException(status_code=500, detail=str(e))


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
        raise HTTPException(status_code=500, detail=str(e))

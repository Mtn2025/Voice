from fastapi import APIRouter
from starlette.responses import RedirectResponse

router = APIRouter()

# Redirections for backward compatibility (Deprecated)
# These will be removed in future versions.

@router.post("/calls/test-outbound", include_in_schema=False)
async def deprecated_test_outbound():
    """
    DEPRECATED: Use /admin/test-call-telnyx
    """
    return RedirectResponse(url="/admin/test-call-telnyx", status_code=307)

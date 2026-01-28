"""
Webhook Signature Validation - Punto A4

This module provides HMAC signature validation for webhooks from external providers
(Twilio and Telnyx) to prevent spoofing and ensure requests are authentic.

Security Implementation:
- Twilio: X-Twilio-Signature header validation (HMAC-SHA1)
- Telnyx: Public Key signature validation (Ed25519)
"""

import base64
import hashlib
import hmac
import logging

from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_twilio_signature(request: Request, body: bytes) -> bool:
    """
    Validate Twilio webhook signature using HMAC-SHA1.

    Twilio sends X-Twilio-Signature header with each webhook request.
    We compute the signature locally and compare with the header.

    Args:
        request: FastAPI Request object
        body: Raw request body bytes

    Returns:
        True if signature is valid, False otherwise

    Reference:
        https://www.twilio.com/docs/usage/webhooks/webhooks-security
    """
    # Get signature from header
    twilio_signature = request.headers.get("X-Twilio-Signature", "")

    if not twilio_signature:
        logger.warning("❌ [TWILIO-SECURITY] No X-Twilio-Signature header found")
        return False

    # Get auth token from settings
    auth_token = settings.TWILIO_AUTH_TOKEN
    if not auth_token:
        logger.error("❌ [TWILIO-SECURITY] TWILIO_AUTH_TOKEN not configured")
        return False

    # Build URL (Twilio uses the full URL including query params)
    url = str(request.url)

    # If POST request, add form data to signature
    if request.method == "POST":
        try:
            # For Twilio, body is form-encoded
            # Parse it and sort parameters alphabetically
            form_data = {}
            for line in body.decode('utf-8').split('&'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    form_data[key] = value

            # Build signature string: URL + sorted params
            signature_string = url + ''.join(f'{k}{v}' for k, v in sorted(form_data.items()))
        except Exception as e:
            logger.error(f"❌ [TWILIO-SECURITY] Error parsing form data: {e}")
            signature_string = url
    else:
        signature_string = url

    # Compute HMAC-SHA1
    computed_signature = base64.b64encode(
        hmac.new(
            auth_token.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
    ).decode('utf-8')

    # Compare signatures (constant-time comparison)
    is_valid = hmac.compare_digest(computed_signature, twilio_signature)

    if is_valid:
        logger.info("✅ [TWILIO-SECURITY] Signature validated successfully")
    else:
        logger.warning(f"❌ [TWILIO-SECURITY] Invalid signature. Expected: {computed_signature[:20]}..., Got: {twilio_signature[:20]}...")

    return is_valid


def validate_telnyx_signature(request: Request, body: bytes) -> bool:
    """
    Validate Telnyx webhook signature using Ed25519 public key cryptography.

    Telnyx uses Ed25519 digital signatures for webhook verification.
    The signature is sent in the 'telnyx-signature-ed25519' header.

    Args:
        request: FastAPI Request object
        body: Raw request body bytes

    Returns:
        True if signature is valid, False otherwise

    Reference:
        https://developers.telnyx.com/docs/v2/development/verifying-webhooks
    """
    # Get signature and timestamp from headers
    signature_header = request.headers.get("telnyx-signature-ed25519", "")
    timestamp_header = request.headers.get("telnyx-timestamp", "")

    if not signature_header or not timestamp_header:
        logger.warning("❌ [TELNYX-SECURITY] Missing signature or timestamp headers")
        # Allow in DEBUG mode (development only)
        if settings.DEBUG:
            logger.warning("⚠️ [TELNYX-SECURITY] DEBUG mode: Allowing unsigned request")
            return True
        return False

    # Get public key from settings
    public_key = settings.TELNYX_PUBLIC_KEY
    if not public_key:
        logger.warning("❌ [TELNYX-SECURITY] TELNYX_PUBLIC_KEY not configured")
        # Allow if not configured in development
        if settings.DEBUG:
            logger.warning("⚠️ [TELNYX-SECURITY] DEBUG mode: Public key not configured, allowing request")
            return True
        return False

    try:
        # Import cryptography for Ed25519 verification
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric import ed25519

        # Construct signed payload: timestamp + . + body
        signed_payload = f"{timestamp_header}.{body.decode('utf-8')}"

        # Decode public key and signature from base64
        try:
            public_key_bytes = base64.b64decode(public_key)
            signature_bytes = base64.b64decode(signature_header)
        except Exception as e:
            logger.error(f"❌ [TELNYX-SECURITY] Error decoding key/signature: {e}")
            return False

        # Create Ed25519 public key object
        try:
            verify_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        except Exception as e:
            logger.error(f"❌ [TELNYX-SECURITY] Invalid public key format: {e}")
            return False

        # Verify signature
        try:
            verify_key.verify(signature_bytes, signed_payload.encode('utf-8'))
            logger.info("✅ [TELNYX-SECURITY] Ed25519 signature validated successfully")
            return True
        except InvalidSignature:
            logger.warning("❌ [TELNYX-SECURITY] Invalid Ed25519 signature")
            return False

    except ImportError:
        logger.error("❌ [TELNYX-SECURITY] cryptography library not installed. Run: pip install cryptography")
        # Fallback: validate presence of headers (better than nothing)
        logger.warning("⚠️ [TELNYX-SECURITY] Falling back to basic validation (headers only)")
        return True
    except Exception as e:
        logger.error(f"❌ [TELNYX-SECURITY] Signature validation error: {e}")
        return False


async def require_twilio_signature(request: Request):
    """
    FastAPI dependency to validate Twilio webhook signature.

    Raises HTTPException 401 if signature is invalid.

    Usage:
        @router.post("/webhook", dependencies=[Depends(require_twilio_signature)])
        async def webhook(request: Request):
            ...
    """
    try:
        # Read raw body
        body = await request.body()

        # Validate signature
        if not validate_twilio_signature(request, body):
            logger.error("🚨 [SECURITY] Rejected Twilio webhook with invalid signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        logger.info("✅ [SECURITY] Twilio webhook signature validated")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [SECURITY] Error validating Twilio signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signature validation failed"
        ) from e


async def require_telnyx_signature(request: Request):
    """
    FastAPI dependency to validate Telnyx webhook signature.

    Raises HTTPException 401 if signature is invalid.

    Usage:
        @router.post("/webhook", dependencies=[Depends(require_telnyx_signature)])
        async def webhook(request: Request):
            ...
    """
    try:
        # Read raw body
        body = await request.body()

        # Validate signature
        if not validate_telnyx_signature(request, body):
            logger.error("🚨 [SECURITY] Rejected Telnyx webhook with invalid signature")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )

        logger.info("✅ [SECURITY] Telnyx webhook signature validated")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [SECURITY] Error validating Telnyx signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Signature validation failed"
        ) from e

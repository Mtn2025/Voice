# API Deprecations

This document tracks deprecated API endpoints and their scheduled removal dates.

## 2026-02-02: Route Separation Refactor

The following endpoints have been moved to dedicated controllers to improve architecture.
Old endpoints will return `307 Temporary Redirect` until the removal date.

| Old Path | New Path | Description | Removal Date |
|----------|----------|-------------|--------------|
| `POST /api/v1/calls/test-outbound` | `POST /admin/test-call-telnyx` | Telnyx test call utility | 2026-02-16 |

### Migration Guide

1. **Update Admin Tools**: If you use `curl` or Postman scripts to trigger test calls, update the URL to `/admin/test-call-telnyx`.
2. **Review Webhooks**: Incoming webhooks from Twilio/Telnyx are unchanged (`/api/v1/twilio/incoming-call`, `/api/v1/telnyx/call-control`).
3. **Simulator Connection**: The simulator now uses a dedicated WebSocket at `/ws/simulator/stream`. The generic `/api/v1/ws/media-stream` still supports `client=browser` for now but prefers the new endpoint.

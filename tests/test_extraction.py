import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.extraction_service import ExtractionService

@pytest.mark.asyncio
async def test_extract_post_call_success():
    # 1. Setup Mock
    mock_client_instance = AsyncMock()
    
    # Mock Response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{
            "message": {
                "content": '{"summary": "Juan wants appointment", "intent": "schedule", "extracted_entities": {"name": "Juan", "phone": "5512345678"}}'
            }
        }]
    }
    mock_response.raise_for_status.return_value = None
    mock_client_instance.post.return_value = mock_response

    # Force singleton to use mock
    with patch("app.core.http_client.http_client.get_client", return_value=mock_client_instance):
        service = ExtractionService()
        
        # 2. Execute
        history = [
            {"role": "assistant", "content": "Hola, ¿con quién hablo?"},
            {"role": "user", "content": "Me llamo Juan y quiero agendar. Mi teléfono es 5512345678."}
        ]
        
        result = await service.extract_post_call("session_123", history)

        # 3. Verify
        assert result["intent"] == "schedule"
        assert result["extracted_entities"]["name"] == "Juan"
        assert result["extracted_entities"]["phone"] == "5512345678"
        
        # Verify call arguments (Schema check)
        args, kwargs = mock_client_instance.post.call_args
        payload = kwargs["json"]
        assert payload["model"] == "llama-3.1-8b-instant"
        assert "messages" in payload
        assert "schema" in payload["messages"][0]["content"].lower()

@pytest.mark.asyncio
async def test_extract_post_call_empty_history():
    service = ExtractionService()
    result = await service.extract_post_call("session_empty", [])
    assert result == {}

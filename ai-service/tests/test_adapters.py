import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from google.api_core import exceptions as google_exceptions

from app.adapters import (
    CircuitBreaker,
    GeminiAdapter,
    LLMMessage,
    OpenAIAdapter,
    get_llm_adapter,
    reset_circuit_breakers,
)
from app.core.config import settings
from app.core.exceptions import (
    CircuitBreakerOpenError,
    LLMConfigurationError,
    LLMRateLimitError,
    LLMTimeoutError,
    mask_sensitive_text,
)


def _fake_gemini_response(text: str = "Xin chào!", prompt_tok: int = 10, comp_tok: int = 20):
    usage = SimpleNamespace(
        prompt_token_count=prompt_tok,
        candidates_token_count=comp_tok,
        total_token_count=prompt_tok + comp_tok,
    )
    return SimpleNamespace(text=text, usage_metadata=usage)


def test_mask_sensitive_text_hides_api_keys(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "AIzaFakeSecretKeyForTesting12345")
    monkeypatch.setattr(settings, "INTERNAL_API_KEY", "MyInternalSecretKey999")
    raw = "Error calling API with key=AIzaFakeSecretKeyForTesting12345 and MyInternalSecretKey999 and sk-proj-abcdef123456"
    masked = mask_sensitive_text(raw)
    assert "AIzaFakeSecretKeyForTesting12345" not in masked
    assert "MyInternalSecretKey999" not in masked
    assert "sk-proj-abcdef123456" not in masked
    assert "***REDACTED***" in masked


def test_gemini_adapter_repr_does_not_leak_key():
    adapter = GeminiAdapter(api_key="AIzaSuperSecret1234567890", model_name="gemini-3.5-flash-lite")
    rep = repr(adapter)
    assert "AIzaSuperSecret1234567890" not in rep
    assert "gemini-3.5-flash-lite" in rep
    assert "configured=True" in rep


@pytest.mark.asyncio
async def test_gemini_adapter_missing_api_key_raises_config_error():
    adapter = GeminiAdapter(api_key="", model_name="gemini-3.5-flash-lite")
    with pytest.raises(LLMConfigurationError):
        await adapter.chat([LLMMessage(role="user", content="Hello")])


@pytest.mark.asyncio
async def test_gemini_adapter_chat_success_and_role_mapping():
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        return_value=_fake_gemini_response("Độ phức tạp là O(n log n).", prompt_tok=12, comp_tok=18)
    )

    with (
        patch("app.adapters.gemini_adapter.genai.configure") as mock_configure,
        patch("app.adapters.gemini_adapter.genai.GenerativeModel", return_value=mock_model) as mock_cls,
    ):
        adapter = GeminiAdapter(api_key="AIzaTestKey123456", model_name="gemini-3.5-flash-lite")
        result = await adapter.chat(
            [
                LLMMessage(role="system", content="Extra system rule."),
                LLMMessage(role="user", content="Merge sort là gì?"),
                LLMMessage(role="assistant", content="Là thuật toán chia để trị."),
                LLMMessage(role="user", content="Độ phức tạp là bao nhiêu?"),
            ],
            system_prompt="Bạn là gia sư.",
            temperature=0.3,
            max_tokens=256,
            response_mime_type="text/plain",
        )

    mock_configure.assert_called_once_with(api_key="AIzaTestKey123456")
    _, init_kwargs = mock_cls.call_args
    assert init_kwargs["model_name"] == "gemini-3.5-flash-lite"
    assert "Bạn là gia sư." in init_kwargs["system_instruction"]
    assert "Extra system rule." in init_kwargs["system_instruction"]

    call_args, call_kwargs = mock_model.generate_content_async.call_args
    contents = call_args[0]
    assert contents == [
        {"role": "user", "parts": ["Merge sort là gì?"]},
        {"role": "model", "parts": ["Là thuật toán chia để trị."]},
        {"role": "user", "parts": ["Độ phức tạp là bao nhiêu?"]},
    ]
    assert call_kwargs["request_options"] == {"timeout": adapter.timeout_seconds}
    assert result.content == "Độ phức tạp là O(n log n)."
    assert result.provider == "gemini"
    assert result.model == "gemini-3.5-flash-lite"
    assert result.tokens_prompt == 12
    assert result.tokens_completion == 18
    assert result.total_tokens == 30


@pytest.mark.asyncio
async def test_gemini_adapter_stream_success():
    async def fake_async_stream():
        yield _fake_gemini_response("Xin ", prompt_tok=5, comp_tok=1)
        yield _fake_gemini_response("chào!", prompt_tok=5, comp_tok=2)

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=fake_async_stream())

    with (
        patch("app.adapters.gemini_adapter.genai.configure"),
        patch("app.adapters.gemini_adapter.genai.GenerativeModel", return_value=mock_model),
    ):
        adapter = GeminiAdapter(api_key="AIzaTestKey123456", model_name="gemini-3.5-flash-lite")
        chunks = []
        async for chunk in adapter.stream([LLMMessage(role="user", content="Hi")]):
            chunks.append(chunk)

    assert [c.delta for c in chunks if not c.done] == ["Xin ", "chào!"]
    assert chunks[-1].done is True
    assert chunks[-1].total_tokens == 7


@pytest.mark.asyncio
async def test_gemini_adapter_retry_then_succeed():
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=[
            google_exceptions.ServiceUnavailable("503 temporary outage"),
            google_exceptions.ResourceExhausted("429 temporary limit"),
            _fake_gemini_response("Thành công sau retry!"),
        ]
    )

    with (
        patch("app.adapters.gemini_adapter.genai.configure"),
        patch("app.adapters.gemini_adapter.genai.GenerativeModel", return_value=mock_model),
        patch("app.adapters.gemini_adapter.asyncio.sleep", new=AsyncMock()),
    ):
        adapter = GeminiAdapter(
            api_key="AIzaTestKey123456",
            model_name="gemini-3.5-flash-lite",
            max_retries=2,
        )
        res = await adapter.chat([LLMMessage(role="user", content="Test retry")])

    assert res.content == "Thành công sau retry!"
    assert mock_model.generate_content_async.call_count == 3


@pytest.mark.asyncio
async def test_gemini_adapter_rate_limit_exhausted_opens_circuit_breaker():
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout=60.0)
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=google_exceptions.ResourceExhausted("429 quota exceeded")
    )

    with (
        patch("app.adapters.gemini_adapter.genai.configure"),
        patch("app.adapters.gemini_adapter.genai.GenerativeModel", return_value=mock_model),
        patch("app.adapters.gemini_adapter.asyncio.sleep", new=AsyncMock()),
    ):
        adapter = GeminiAdapter(
            api_key="AIzaTestKey123456",
            max_retries=1,
            circuit_breaker=breaker,
        )
        with pytest.raises(LLMRateLimitError):
            await adapter.chat([LLMMessage(role="user", content="Call 1")])
        with pytest.raises(LLMRateLimitError):
            await adapter.chat([LLMMessage(role="user", content="Call 2")])
        with pytest.raises(CircuitBreakerOpenError):
            await adapter.chat([LLMMessage(role="user", content="Call 3 blocked")])


@pytest.mark.asyncio
async def test_gemini_adapter_timeout_raises_llm_timeout_error():
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(side_effect=asyncio.TimeoutError())

    with (
        patch("app.adapters.gemini_adapter.genai.configure"),
        patch("app.adapters.gemini_adapter.genai.GenerativeModel", return_value=mock_model),
        patch("app.adapters.gemini_adapter.asyncio.sleep", new=AsyncMock()),
    ):
        adapter = GeminiAdapter(api_key="AIzaTestKey123456", max_retries=1, timeout_seconds=1.0)
        with pytest.raises(LLMTimeoutError):
            await adapter.chat([LLMMessage(role="user", content="Slow query")])


def test_get_llm_adapter_factory(monkeypatch):
    reset_circuit_breakers()
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    assert isinstance(get_llm_adapter(), GeminiAdapter)

    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    assert isinstance(get_llm_adapter(), OpenAIAdapter)

    with pytest.raises(LLMConfigurationError):
        get_llm_adapter("unknown_provider")


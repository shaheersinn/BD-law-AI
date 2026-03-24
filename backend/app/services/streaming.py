"""
app/services/streaming.py — Server-Sent Events for real-time AI streaming.

Partners see tokens appearing in real time instead of waiting 10-30s for a
complete response. Dramatically improves perceived performance.

Usage:
    @router.get("/clients/{id}/churn-brief/stream")
    async def stream_brief(id: int):
        return StreamingResponse(
            stream_ai_response("churn_brief", name="...", ...),
            media_type="text/event-stream",
        )

SSE format:
    data: {"delta": "token text here"}\n\n
    data: {"done": true, "full_text": "complete response"}\n\n
    data: [DONE]\n\n
"""

import json
import logging
from collections.abc import AsyncIterator

import anthropic

from app.config import get_settings
from app.services.anthropic_service import PROMPTS

log = logging.getLogger(__name__)
settings = get_settings()


async def stream_ai_response(
    prompt_key: str,
    **kwargs,
) -> AsyncIterator[str]:
    """
    Streams an AI response as Server-Sent Events.
    Yields SSE-formatted strings.
    Falls back to single-shot response if streaming fails.
    """
    template = PROMPTS.get(prompt_key)
    if not template:
        yield f"data: {json.dumps({'error': f'Unknown prompt key: {prompt_key}'})}\n\n"
        return

    try:
        prompt = template.format(**kwargs)
    except KeyError as e:
        yield f"data: {json.dumps({'error': f'Missing prompt variable: {e}'})}\n\n"
        return

    if not settings.anthropic_api_key:
        # Fallback: non-streaming Groq
        from app.services.anthropic_service import ai

        try:
            text = await ai._call_groq(prompt)
            yield f"data: {json.dumps({'delta': text})}\n\n"
            yield f"data: {json.dumps({'done': True, 'full_text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        return

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    full_text = []

    try:
        async with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                full_text.append(text)
                yield f"data: {json.dumps({'delta': text})}\n\n"

        complete = "".join(full_text)
        yield f"data: {json.dumps({'done': True, 'full_text': complete})}\n\n"
        yield "data: [DONE]\n\n"

    except anthropic.RateLimitError:
        yield f"data: {json.dumps({'error': 'Rate limit reached — try again in 60 seconds'})}\n\n"
    except anthropic.AuthenticationError:
        yield f"data: {json.dumps({'error': 'API key invalid or not configured'})}\n\n"
    except Exception as e:
        log.error("Stream error for %s: %s", prompt_key, e)
        yield f"data: {json.dumps({'error': 'Generation failed — please retry'})}\n\n"


def sse_headers() -> dict:
    """Standard headers for SSE responses."""
    return {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
    }

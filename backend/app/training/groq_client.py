"""
app/training/groq_client.py — Async Groq API client for Phase 4 pseudo-labeling.

Handles:
  - Rate limiting (600 req/min ceiling)
  - Batch processing (GROQ_BATCH_SIZE signals per API call)
  - JSON response parsing with graceful fallback to "uncertain"
  - Structured dataclasses for inputs/outputs (no ORM dependency)

IMPORTANT: Groq API is used for training pseudo-labeling ONLY.
           It is NEVER called in production scoring paths.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from app.config import get_settings

log = structlog.get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_BASE = "https://api.groq.com/openai/v1"
GROQ_RPM_LIMIT = 600  # requests per minute (free tier ceiling)
GROQ_BATCH_SIZE = 10  # signals classified per API call
GROQ_REQUEST_TIMEOUT = 60  # seconds per request
GROQ_MAX_TOKENS = 1024  # per response (enough for 10-signal JSON batch)
GROQ_TEMPERATURE = 0.1  # very low: deterministic classification


# ── Data Transfer Objects ──────────────────────────────────────────────────────


@dataclass
class SignalInput:
    """Lightweight container for a signal record to be classified."""

    signal_id: int
    signal_type: str
    signal_text: str | None
    company_id: int
    # Optional: pre-existing hint from scraper
    practice_area_hint: str | None = None


@dataclass
class ClassificationResult:
    """Output of a single Groq classification for one signal."""

    signal_id: int
    label_type: str  # "positive" | "negative" | "uncertain"
    practice_areas: list[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    parse_error: bool = False  # True if JSON parsing failed


# ── Groq Client ───────────────────────────────────────────────────────────────


class GroqClient:
    """
    Async Groq API client optimised for batch signal classification.

    Rate-limits to GROQ_RPM_LIMIT requests/min via inter-batch sleeps.
    Falls back to 'uncertain' on any parse or network error (never raises
    unless the caller explicitly propagates).
    """

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.groq_api_key
        if not self._api_key:
            log.warning("GROQ_API_KEY not set — pseudo-labeling will fail at runtime")

    async def classify_signals(
        self,
        signals: list[SignalInput],
        prompt_builder: Any = None,  # callable(list[SignalInput]) -> str
    ) -> list[ClassificationResult]:
        """
        Classify a list of signals in batches.

        Injects rate-limit sleep between batches to stay within GROQ_RPM_LIMIT.
        Falls back to 'uncertain' result on any individual batch failure.

        Args:
            signals: signals to classify (any length)
            prompt_builder: callable(list[SignalInput]) -> str.
                            Defaults to app.training.prompts.build_classification_prompt.

        Returns:
            List of ClassificationResult in the same order as input signals.
        """
        if prompt_builder is None:
            from app.training.prompts import build_classification_prompt

            prompt_builder = build_classification_prompt

        results: list[ClassificationResult] = []
        batches = [
            signals[i : i + GROQ_BATCH_SIZE] for i in range(0, len(signals), GROQ_BATCH_SIZE)
        ]

        # Sleep between batches to stay under rate limit
        # Each batch = 1 API call; GROQ_RPM_LIMIT calls per 60s
        inter_batch_sleep = GROQ_BATCH_SIZE / GROQ_RPM_LIMIT * 60.0

        for batch_idx, batch in enumerate(batches):
            if batch_idx > 0:
                await asyncio.sleep(inter_batch_sleep)

            try:
                prompt = prompt_builder(batch)
                raw = await self._call_once(prompt)
                batch_results = self._parse_response(raw, batch)
            except Exception as exc:  # noqa: BLE001
                log.error(
                    "Groq batch failed — defaulting to uncertain",
                    batch_idx=batch_idx,
                    batch_size=len(batch),
                    error=str(exc),
                )
                batch_results = [
                    ClassificationResult(
                        signal_id=s.signal_id,
                        label_type="uncertain",
                        confidence=0.0,
                        parse_error=True,
                    )
                    for s in batch
                ]

            results.extend(batch_results)
            log.debug(
                "Groq batch classified",
                batch_idx=batch_idx,
                batch_size=len(batch),
                results=len(batch_results),
            )

        return results

    async def _call_once(self, prompt: str) -> str:
        """Single Groq API call. Raises on HTTP error."""
        settings = get_settings()
        api_key = self._api_key or settings.groq_api_key

        async with httpx.AsyncClient(timeout=GROQ_REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{GROQ_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": GROQ_MAX_TOKENS,
                    "temperature": GROQ_TEMPERATURE,
                },
            )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]  # type: ignore[no-any-return]

    def _parse_response(self, raw: str, batch: list[SignalInput]) -> list[ClassificationResult]:
        """
        Parse JSON array from Groq response.

        Expected format:
          [{"signal_id": 1, "label_type": "positive",
            "practice_areas": ["M&A/Corporate"], "confidence": 0.85,
            "reasoning": "..."}]

        Falls back to 'uncertain' per-signal if JSON is malformed.
        """
        # Strip markdown fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        signal_map = {s.signal_id: s for s in batch}

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            log.warning("Groq JSON parse failed", error=str(exc), raw_prefix=raw[:200])
            return [
                ClassificationResult(
                    signal_id=s.signal_id,
                    label_type="uncertain",
                    confidence=0.0,
                    parse_error=True,
                )
                for s in batch
            ]

        results: list[ClassificationResult] = []
        seen_ids: set[int] = set()

        if not isinstance(parsed, list):
            parsed = [parsed]

        for item in parsed:
            if not isinstance(item, dict):
                continue
            try:
                sid = int(item["signal_id"])
            except (KeyError, TypeError, ValueError):
                continue

            if sid not in signal_map:
                continue

            label_type = str(item.get("label_type", "uncertain")).lower()
            if label_type not in ("positive", "negative", "uncertain"):
                label_type = "uncertain"

            pas = item.get("practice_areas") or []
            if not isinstance(pas, list):
                pas = [pas] if pas else []

            conf = float(item.get("confidence", 0.0))
            conf = max(0.0, min(1.0, conf))

            results.append(
                ClassificationResult(
                    signal_id=sid,
                    label_type=label_type,
                    practice_areas=[str(p) for p in pas],
                    confidence=conf,
                    reasoning=str(item.get("reasoning", "")),
                )
            )
            seen_ids.add(sid)

        # Fill in any signals missing from Groq's response
        for sig in batch:
            if sig.signal_id not in seen_ids:
                results.append(
                    ClassificationResult(
                        signal_id=sig.signal_id,
                        label_type="uncertain",
                        confidence=0.0,
                        parse_error=True,
                    )
                )

        return results


# ── Module-level logger (structlog) ───────────────────────────────────────────
logging.getLogger(__name__)

"""
app/training/prompts.py — Groq prompt templates for Phase 4 signal classification.

Provides few-shot JSON prompts that instruct the LLM to:
  1. Classify each signal as positive | negative | uncertain
  2. Assign one or more of the 34 canonical practice areas
  3. Return a confidence score (0.0-1.0) and brief reasoning

Output format: JSON array matching the input signals 1:1 by signal_id.
"""

from __future__ import annotations

from app.training.groq_client import SignalInput

# ── System Persona ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert legal intelligence analyst for a Canadian BigLaw firm.
Your job is to classify corporate signals to predict which companies will need legal counsel.

You analyze signals from regulatory filings, news sources, court records, and market data
to determine:
1. Whether the signal is POSITIVE (indicates near-term legal need), NEGATIVE (no legal need),
   or UNCERTAIN (insufficient information)
2. Which of the 34 Canadian legal practice areas are relevant
3. Your confidence level (0.0 to 1.0)

Always respond with valid JSON only. No prose outside the JSON array."""

# ── Few-Shot Examples ──────────────────────────────────────────────────────────

FEW_SHOT_EXAMPLES = [
    {
        "signal_id": -1,
        "signal_type": "ccaa_filing",
        "signal_text": (
            "Acme Corp has filed for creditor protection under the Companies' "
            "Creditors Arrangement Act at the Ontario Superior Court of Justice, "
            "listing $450M in liabilities."
        ),
        "label_type": "positive",
        "practice_areas": ["Insolvency/Restructuring"],
        "confidence": 0.97,
        "reasoning": (
            "CCAA filing is direct evidence of imminent insolvency/restructuring legal engagement."
        ),
    },
    {
        "signal_id": -2,
        "signal_type": "job_posting",
        "signal_text": (
            "Senior Software Engineer — Python/Django, 5+ years experience, remote. "
            "Competitive salary and benefits."
        ),
        "label_type": "negative",
        "practice_areas": [],
        "confidence": 0.93,
        "reasoning": (
            "Technical job posting with no legal implications. "
            "Engineering roles do not signal legal counsel needs."
        ),
    },
    {
        "signal_id": -3,
        "signal_type": "regulatory_sanction",
        "signal_text": (
            "The company received a notice from Environment and Climate Change Canada "
            "regarding potential non-compliance with emission reporting standards "
            "under the Canadian Environmental Protection Act."
        ),
        "label_type": "positive",
        "practice_areas": ["Environmental/Indigenous/Energy", "Regulatory/Compliance"],
        "confidence": 0.81,
        "reasoning": (
            "CEPA non-compliance notice strongly indicates need for environmental "
            "regulatory counsel. Multi-practice area: primary environmental, "
            "secondary regulatory compliance."
        ),
    },
    {
        "signal_id": -4,
        "signal_type": "earnings_release",
        "signal_text": (
            "Q3 revenue of $1.2B, up 8% YoY. EBITDA margin improved to 24%. "
            "Management reaffirms full-year guidance."
        ),
        "label_type": "negative",
        "practice_areas": [],
        "confidence": 0.88,
        "reasoning": (
            "Routine earnings release with positive financial results. "
            "No indication of legal, regulatory, or transactional needs."
        ),
    },
    {
        "signal_id": -5,
        "signal_type": "material_change_report",
        "signal_text": (
            "The company has entered into a non-binding letter of intent to acquire "
            "a competitor for approximately $800M in a combination of cash and shares, "
            "subject to regulatory approval."
        ),
        "label_type": "positive",
        "practice_areas": ["M&A/Corporate", "Competition/Antitrust", "Securities/Capital Markets"],
        "confidence": 0.94,
        "reasoning": (
            "M&A transaction at this scale requires corporate M&A counsel, "
            "competition/antitrust review (likely requires Competition Bureau approval), "
            "and securities law for the share component."
        ),
    },
]


def _format_examples() -> str:
    """Format few-shot examples as input/output pairs in the prompt."""
    lines: list[str] = []
    lines.append("## Few-Shot Examples\n")
    lines.append("Input signals:")
    import json

    input_signals = [
        {
            "signal_id": ex["signal_id"],
            "signal_type": ex["signal_type"],
            "signal_text": ex["signal_text"],
        }
        for ex in FEW_SHOT_EXAMPLES
    ]
    lines.append(json.dumps(input_signals, indent=2))
    lines.append("\nExpected JSON output:")
    output = [
        {
            "signal_id": ex["signal_id"],
            "label_type": ex["label_type"],
            "practice_areas": ex["practice_areas"],
            "confidence": ex["confidence"],
            "reasoning": ex["reasoning"],
        }
        for ex in FEW_SHOT_EXAMPLES
    ]
    lines.append(json.dumps(output, indent=2))
    return "\n".join(lines)


# ── Main Prompt Builder ────────────────────────────────────────────────────────


def build_classification_prompt(signals: list[SignalInput]) -> str:
    """
    Build a Groq prompt to classify a batch of signals.

    Args:
        signals: list of SignalInput (max GROQ_BATCH_SIZE)

    Returns:
        Complete prompt string including system context, few-shot examples,
        practice area list, output schema, and the batch to classify.
    """
    import json

    from app.ground_truth.constants import PRACTICE_AREAS

    # Format input batch
    batch_input = []
    for sig in signals:
        entry: dict[str, object] = {
            "signal_id": sig.signal_id,
            "signal_type": sig.signal_type,
            "signal_text": sig.signal_text or "(no text — classify by signal_type only)",
        }
        if sig.practice_area_hint:
            entry["hint"] = sig.practice_area_hint
        batch_input.append(entry)

    pa_list = "\n".join(f"  - {pa}" for pa in PRACTICE_AREAS)

    prompt = f"""{SYSTEM_PROMPT}

---

{_format_examples()}

---

## Valid Practice Areas (use EXACT spelling)

{pa_list}

---

## Output Schema

Return a JSON array with one object per input signal. Fields:
- signal_id: integer (same as input)
- label_type: "positive" | "negative" | "uncertain"
  - positive: company likely needs legal counsel within 30-90 days
  - negative: no legal engagement expected
  - uncertain: insufficient information to classify
- practice_areas: array of strings from the valid list above (empty array for negative)
- confidence: float 0.0-1.0 (your certainty in this classification)
- reasoning: 1-2 sentence explanation

Rules:
- ALWAYS return one JSON object per input signal, in the same order
- ONLY use practice areas from the valid list (exact spelling)
- For negative signals, practice_areas MUST be an empty array []
- confidence < 0.60 → use label_type "uncertain"
- Respond with ONLY the JSON array, no prose before or after

---

## Signals to Classify

{json.dumps(batch_input, indent=2)}

JSON output:"""

    return prompt

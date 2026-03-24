"""
app/services/anthropic_service.py — Claude API service layer.

All AI generation lives here. Every method takes structured data and returns
plain text. The API key is read from settings — never passed by the caller.
Includes a Groq fallback (free, 14 400 req/day) when the Anthropic key is unset.
"""

import logging

import anthropic
import httpx

from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# ── Prompts ────────────────────────────────────────────────────────────────────

PROMPTS = {
    "churn_brief": """You are a BigLaw BD AI. Write a concise partner action brief (under 180 words) for this at-risk client.

Client: {name}
Industry: {industry}
Flight Risk Score: {score}/100 ({risk} RISK)
Partner: {partner}
Revenue: {revenue}/yr
Last Contact: {contact_days} days ago
Active Matter: {matter}

Risk signals:
{signals}

Provide: (1) Root cause analysis — 2-3 sentences (2) Immediate recommended action with timing (3) One non-obvious insight.
Direct, no headers, plain text. Partner reads on their phone.""",
    "regulatory_alert": """Draft a proactive client alert (150-180 words) from a Canadian law firm to this client about the regulatory update.

Update: {source} — {title}
Date: {date}
Practice area: {practice_area}

Client: {client_name}, {industry}, {region}
Active matter: {matter}
Practice groups: {practice_groups}

Professional email style, first person plural ("we"). Include: (1) What changed (2) Why it specifically affects this client (3) One concrete recommended action (4) Offer to discuss. Under 180 words. Plain text only, no subject line.""",
    "prospect_outreach": """BigLaw BD AI. Generate outreach strategy brief (under 140 words) for this prospect.

Company: {name}
Legal Urgency Score: {score}/100
Predicted Need: {need}
Relationship: {warmth}
Est. Value: {value}
Window: {window}

Signals:
{signals}

Provide: (1) The one insight creating urgency to call NOW (2) Exact opening line to use (3) What to offer in first call. Specific, direct, plain text.""",
    "jet_brief": """BigLaw M&A BD. A corporate jet track has fired a mandate signal.

Company: {company}
Aircraft: {tail}
Executive: {executive}
Route: {origin} → {destination}
Date: {date}
Signal: {signal}
Predicted mandate: {mandate}
Confidence: {confidence}%
Relationship warmth: {warmth}/100

Write a 120-word tactical action brief:
1. Why this jet track means a mandate is imminent
2. Exactly which partner should call and why
3. The opening line that demonstrates intelligence without revealing surveillance
4. What to pitch in the first 5 minutes

Direct, plain text. No headers.""",
    "foot_traffic_strategy": """BigLaw BD AI. A client has been detected at a competitor law firm.

Client: {client}
Location detected: {location}
Device cluster: {devices} devices · {duration}
Date: {date}
Threat: {threat}
Severity: {severity}

Write a 100-word response strategy:
1. What this likely means
2. Which partner acts and what they say
3. Whether to use conflict arbitrage
4. Exact tone — urgent but not panicked

Plain text. Direct.""",
    "satellite_brief": """BigLaw BD analyst. Satellite intelligence signal detected.

Company: {company}
Location: {location}
Observation: {observation}
Inference: {inference}
Signal type: {signal_type}
Confidence: {confidence}%
Urgency: {urgency}

Write a 120-word legal exposure brief:
1. What this observation legally means for the company
2. Which specific matter is forming (be exact — cite the statute, e.g. WSIB s.40 notice period)
3. Which practice group calls, what they offer, and the opening line
4. Timeline: days until this becomes a public event

Direct, specific, plain text.""",
    "permit_brief": """BigLaw BD analyst. A significant permit filing predicts legal work.

Company: {company}
Permit: {permit}
Location: {location}
Filed: {filed}
Project: {project_type}
Practice areas triggered: {work}
Est. legal value: {fee}
Urgency: {urgency}
{relationship_line}

Write a 120-word outreach brief:
1. Why this permit means legal work is imminent (cite the regulatory step)
2. Exact sequence of legal matters this project generates, in order
3. Which partner calls, what they say, and when
4. Opening line

Direct, plain text.""",
    "mandate_brief": """ORACLE synthesis AI. A mandate is forming.

Company: {company}
Signals converged within {window}:
{signals}

Confidence: {confidence}%
Predicted Practice: {practice}
Est. Value: {value}

Provide: (1) One sentence — why to call TODAY (2) Who at firm should call (3) Exact first sentence when GC answers (4) What to offer in first 5 minutes.

Plain text. Partner reads on phone. Urgent where warranted.""",
    "alumni_message": """Draft a personal message from {mentor} (BigLaw partner) to former associate {name} (now {role} at {company}). They left in {departure_year}.
The message must feel genuinely personal, NOT like a sales pitch.

Active trigger: {trigger}

Under 100 words. Open with a genuine personal touch (not "Hope this finds you well"). Reference something natural about their role. Mention the legal development casually. End with a low-pressure ask. Plain text only.""",
    "gc_profile": """Build a GC psychographic profile for law firm BD. Return ONLY valid JSON, no markdown.

Company: {company}
Public information:
{information}

{{"name":"string","title":"string","decision_style":"string","risk_tolerance":"Low/Medium/High","communication_pref":"string","fee_sensitivity":"string","career_ambition":"string","key_concerns":["str","str","str"],"pitch_hooks":["str","str","str"],"credibility":65,"reliability":70,"intimacy":50,"self_orientation":40,"trust_score":62,"brief":"2-3 sentence pre-meeting brief for senior partner"}}""",
    "trigger_brief": """BigLaw BD analyst. A legal trigger signal just fired.

Source: {source}
Signal: {trigger_type}
Company: {company}
Practice area: {practice_area}
Urgency: {urgency}/100
Description: {description}
Filed: {filed}

Write a 120-word partner action brief:
1. What this signal almost certainly means for the company
2. The specific legal matter type predicted and approximate fee
3. Which partner should call and why
4. The exact opening line — demonstrates knowledge without revealing surveillance

Direct, plain text. Partner reads on phone.""",
    "coaching_brief": """You are a BigLaw BD performance coach. Analyse this partner's data and write 4 specific coaching observations. Each must cite actual numbers. Each must end with a concrete action for THIS WEEK — not 'consider', a specific directive.

Partner: {name} ({role})
Top referral source: {top_source} ({top_count} matters)
Stale referrals: {stale_referrers}
Open follow-ups unresolved: {open_followups}
Fast follow-up win rate (within 48h): {fast_win_rate}%
Slow follow-up win rate: {slow_win_rate}%
Days since last content: {last_content_days}
Best content type: {best_content_type}
CLE talks in 6 months: {talks}

Style: direct, specific, respectful. Like a great coach. Max 280 words. Plain text, no headers.""",
    "linkedin_draft": """You are ghostwriting a LinkedIn post for {name}, {title} at {firm}.
Their writing style — match this exactly:
{writing_samples}

Development to write about:
{topic}

Rules:
- 200 to 260 words exactly
- Open with the business implication for GCs and CLOs — NOT "I am pleased to share"
- One concrete takeaway for the reader
- End with a question that prompts comments
- Maximum 3 hashtags at the very end
- Sound like a senior practitioner writing to peers, not a press release
- Do not use: "game-changer", "exciting", "thrilled", "proud to", "unpacking", "deep dive"

Output the post only. No preamble.""",
    "pitch_debrief": """Analyze this lost pitch debrief. Under 140 words. Direct.

{debrief}

Provide: (1) Most likely root cause of loss (2) What winning firm likely did differently (3) One specific improvement for next pitch (4) Re-pitch in 6 months or walk away? Plain text.""",
    "bd_campaign": """Design a 4-step 6-week BD campaign for {client_name} ({industry}). Active matter: {matter}. Partner: {partner}. Wallet share: {wallet_share}% (room to grow). Flight risk: {churn_score}/100.

For each step specify: week, channel (email/call/event/memo), sender, content angle, expected client action. Under 220 words. Plain text, simple numbering.""",
    "geo_brief": """BigLaw BD AI. Write a 130-word market intelligence brief for a Canadian firm considering a BD push into {jurisdiction}.

Legal demand index: {index}/100
Top practice areas: {practice}
Key drivers: {drivers}

Provide: (1) Highest-value opportunity for a Canadian firm right now (2) Which existing client relationships have cross-border exposure (3) One concrete BD action this quarter — event, thought leadership, or referral network. Plain text, direct, no headers.""",
    "ma_strategy": """M&A BD AI. Write outreach strategy (under 140 words) for pre-announcement deal intelligence.

Company: {company}
Deal type: {deal_type}
Est. Value: {value}
Days to announcement: {days}
Confidence: {confidence}%
Warmth: {warmth}/100

Signals:
{signals}

Provide: (1) Which legal seats to pitch (buy-side/sell-side/target board/financing/regulatory clearance) (2) ONE opening line that demonstrates intelligence without revealing surveillance (3) What to offer in first call.

Specific, direct, plain text.""",
}


# ── Client ─────────────────────────────────────────────────────────────────────


class AnthropicService:
    """
    Thin wrapper around the Anthropic Python SDK.
    All public methods accept plain dicts and return str.
    """

    def __init__(self) -> None:
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def generate(self, prompt_key: str, **kwargs: object) -> str:
        """
        Generate text using a named prompt template.
        Falls back to Groq if Anthropic key is unavailable.
        """
        template = PROMPTS.get(prompt_key)
        if not template:
            raise ValueError(f"Unknown prompt key: {prompt_key}")

        try:
            prompt = template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing prompt variable {e} for key '{prompt_key}'") from e

        if settings.anthropic_api_key:
            return await self._call_anthropic(prompt)
        elif settings.groq_api_key:
            return await self._call_groq(prompt)
        else:
            return "[API key not configured — set ANTHROPIC_API_KEY in environment variables]"

    async def _call_anthropic(self, prompt: str) -> str:
        client = self._get_client()
        message = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    async def _call_groq(self, prompt: str) -> str:
        """
        Free Groq fallback — 14 400 req/day, Llama 3.1 70b.
        Same quality as GPT-4 class on legal drafting tasks.
        """
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama-3.1-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": settings.anthropic_max_tokens,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


# Singleton — import and use directly
ai = AnthropicService()

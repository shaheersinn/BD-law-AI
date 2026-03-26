# ruff: noqa: S311  — load tests use random for data generation, not cryptography
"""
tests/load/locustfile.py — ORACLE load test suite.

Three Locust user classes simulating real BD analyst traffic patterns:

1. PartnerUser  — heavy score + explain reads, occasional mandate confirmation
2. AnalystUser  — company search + signal feed browsing, batch score requests
3. AdminUser    — metrics + scraper health checks (low frequency)

Usage:
    # Headless (CI)
    locust -f tests/load/locustfile.py --headless -u 50 -r 5 --run-time 2m \
           --host http://localhost:8000

    # Interactive UI
    locust -f tests/load/locustfile.py --host http://localhost:8000

Target SLOs (from HANDOFF):
    p95 latency for GET /v1/scores/{id}   < 200ms
    p95 latency for POST /v1/scores/batch < 500ms
    Error rate                            < 0.1%
"""

from __future__ import annotations

import os
import random

from locust import HttpUser, between, task

# ── Test data ──────────────────────────────────────────────────────────────────

_COMPANY_IDS = list(range(1, 101))  # Companies 1–100
_PRACTICE_AREAS = [
    "M&A/Corporate",
    "Litigation/Dispute Resolution",
    "Regulatory/Compliance",
    "Employment/Labour",
    "Insolvency/Restructuring",
    "Securities/Capital Markets",
    "Privacy/Cybersecurity",
]

_PARTNER_TOKEN = os.environ.get("LOAD_TEST_PARTNER_TOKEN", "test-partner-token")
_ADMIN_TOKEN = os.environ.get("LOAD_TEST_ADMIN_TOKEN", "test-admin-token")


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── User Classes ───────────────────────────────────────────────────────────────


class PartnerUser(HttpUser):
    """
    Senior partner — reviews scores and SHAP explanations for priority companies.
    Occasionally confirms mandates via the feedback endpoint.

    Wait time: 1–5 seconds between tasks (deliberate reading pace).
    """

    wait_time = between(1, 5)
    weight = 3  # 3× more partner users than admin

    def on_start(self) -> None:
        self.headers = _auth_headers(_PARTNER_TOKEN)
        self.company_id = random.choice(_COMPANY_IDS)

    @task(10)
    def get_company_score(self) -> None:
        """Fetch the 34×3 score matrix for a company."""
        cid = random.choice(_COMPANY_IDS)
        with self.client.get(
            f"/api/v1/scores/{cid}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/scores/[id]",
        ) as resp:
            if resp.status_code == 404:
                resp.success()  # Not found is expected for synthetic IDs

    @task(5)
    def get_score_explanation(self) -> None:
        """Fetch SHAP counterfactuals for a company."""
        cid = random.choice(_COMPANY_IDS)
        with self.client.get(
            f"/api/v1/scores/{cid}/explain",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/scores/[id]/explain",
        ) as resp:
            if resp.status_code == 404:
                resp.success()

    @task(3)
    def batch_score(self) -> None:
        """Batch score 10 companies."""
        ids = random.sample(_COMPANY_IDS, k=10)
        areas = random.sample(_PRACTICE_AREAS, k=3)
        self.client.post(
            "/api/v1/scores/batch",
            json={"company_ids": ids, "practice_areas": areas},
            headers=self.headers,
            name="/api/v1/scores/batch",
        )

    @task(2)
    def get_top_velocity(self) -> None:
        """Fetch top velocity dashboard widget."""
        self.client.get(
            "/api/v1/scores/top-velocity?limit=20",
            headers=self.headers,
            name="/api/v1/scores/top-velocity",
        )

    @task(1)
    def confirm_mandate(self) -> None:
        """Submit a mandate confirmation (low frequency)."""
        self.client.post(
            "/api/v1/feedback/mandate",
            json={
                "company_id": random.choice(_COMPANY_IDS),
                "practice_area": random.choice(_PRACTICE_AREAS),
                "confirmation_source": "load_test",
            },
            headers=self.headers,
            name="/api/v1/feedback/mandate",
        )

    @task(4)
    def get_feedback_accuracy(self) -> None:
        """Fetch accuracy metrics dashboard."""
        self.client.get(
            "/api/v1/feedback/accuracy?days=90",
            headers=self.headers,
            name="/api/v1/feedback/accuracy",
        )


class AnalystUser(HttpUser):
    """
    BD analyst — searches for companies, browses signal feeds, runs batch scores.
    More frequent, shorter sessions.

    Wait time: 0.5–2 seconds (faster browsing pace).
    """

    wait_time = between(0.5, 2)
    weight = 5  # Most common user type

    def on_start(self) -> None:
        self.headers = _auth_headers(_PARTNER_TOKEN)

    @task(8)
    def search_companies(self) -> None:
        """Fuzzy company search."""
        queries = ["acme", "tech", "bank", "mining", "pharma", "media"]
        q = random.choice(queries)
        self.client.get(
            f"/api/v1/companies/search?q={q}&limit=15",
            headers=self.headers,
            name="/api/v1/companies/search",
        )

    @task(6)
    def get_company_profile(self) -> None:
        """Company profile + latest features."""
        cid = random.choice(_COMPANY_IDS)
        with self.client.get(
            f"/api/v1/companies/{cid}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/companies/[id]",
        ) as resp:
            if resp.status_code == 404:
                resp.success()

    @task(5)
    def get_signal_feed(self) -> None:
        """Browse signal feed for a company."""
        cid = random.choice(_COMPANY_IDS)
        with self.client.get(
            f"/api/v1/signals/{cid}?limit=50",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/signals/[id]",
        ) as resp:
            if resp.status_code == 404:
                resp.success()

    @task(3)
    def get_trends(self) -> None:
        """Practice area trend charts."""
        self.client.get(
            "/api/v1/trends/practice_areas",
            headers=self.headers,
            name="/api/v1/trends/practice_areas",
        )

    @task(2)
    def batch_score_small(self) -> None:
        """Small batch score (5 companies)."""
        ids = random.sample(_COMPANY_IDS, k=5)
        self.client.post(
            "/api/v1/scores/batch",
            json={"company_ids": ids},
            headers=self.headers,
            name="/api/v1/scores/batch",
        )

    @task(1)
    def health_check(self) -> None:
        """Periodic health check (mimics frontend polling)."""
        self.client.get("/api/health", name="/api/health")


class AdminUser(HttpUser):
    """
    System admin — monitors scraper health, metrics, and drift alerts.
    Very low frequency.

    Wait time: 10–30 seconds.
    """

    wait_time = between(10, 30)
    weight = 1  # Rare

    def on_start(self) -> None:
        self.headers = _auth_headers(_ADMIN_TOKEN)

    @task(5)
    def check_scraper_health(self) -> None:
        """Scraper health dashboard."""
        self.client.get(
            "/api/v1/scrapers/health",
            headers=self.headers,
            name="/api/v1/scrapers/health",
        )

    @task(3)
    def get_drift_alerts(self) -> None:
        """Check open model drift alerts."""
        self.client.get(
            "/api/v1/feedback/drift",
            headers=self.headers,
            name="/api/v1/feedback/drift",
        )

    @task(2)
    def scrape_metrics(self) -> None:
        """Prometheus metrics scrape."""
        self.client.get(
            "/api/v1/metrics",
            headers=self.headers,
            name="/api/v1/metrics",
        )

    @task(1)
    def readiness_check(self) -> None:
        """Readiness probe."""
        self.client.get("/api/ready", name="/api/ready")

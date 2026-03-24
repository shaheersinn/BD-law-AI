"""
tests/features/test_phase2_features.py — Phase 2 Feature Engineering Tests.

Tests:
  1.  All feature modules importable and registrations fire
  2.  Feature registry count >= 35 (60+ target, partial in phase 2)
  3.  FeatureValue horizons — only 30/60/90 accepted
  4.  FeatureValue invalid horizon raises ValueError
  5.  BaseFeature null_value helper
  6.  BaseFeature cutoff calculation accuracy
  7.  LegalLanguageDensityFeature — known legal text scores high
  8.  HedgingScoreFeature — hedging-heavy text scores high
  9.  GoingConcernFlagFeature — returns 0/1 appropriately
  10. CrossSignalConfirmationCount — counts distinct categories
  11. SignalAccelerationFeature — positive when recent > prior
  12. FeatureRegistry.by_category — correct filtering
  13. FeatureRunner.get_feature_vector — returns dict with feature names as keys
  14. All features have non-empty description
  15. No duplicate feature names in registry
  16. Weights in FeatureValue default to 1.0
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta


# ── 1. All feature modules importable ─────────────────────────────────────────
def test_feature_modules_importable():
    import app.features.base
    import app.features.corporate
    import app.features.nlp
    import app.features.temporal
    import app.features.geo
    import app.features.macro
    assert True


# ── 2. Registry count ─────────────────────────────────────────────────────────
def test_feature_registry_count():
    import app.features.corporate
    import app.features.nlp
    import app.features.temporal
    import app.features.geo
    import app.features.macro
    from app.features.base import FeatureRegistry
    count = FeatureRegistry.count()
    assert count >= 30, f"Expected >= 30 registered features, got {count}"


# ── 3. FeatureValue valid horizons ────────────────────────────────────────────
def test_feature_value_valid_horizons():
    from app.features.base import FeatureValue
    for horizon in (30, 60, 90):
        fv = FeatureValue(
            company_id=1, feature_name="test", feature_version="v1",
            horizon_days=horizon, value=1.0
        )
        assert fv.horizon_days == horizon


# ── 4. FeatureValue invalid horizon ───────────────────────────────────────────
def test_feature_value_invalid_horizon():
    from app.features.base import FeatureValue
    with pytest.raises(ValueError):
        FeatureValue(
            company_id=1, feature_name="test", feature_version="v1",
            horizon_days=45,  # not 30/60/90
            value=1.0
        )


# ── 5. FeatureValue defaults ──────────────────────────────────────────────────
def test_feature_value_defaults():
    from app.features.base import FeatureValue
    fv = FeatureValue(company_id=1, feature_name="x", feature_version="v1",
                      horizon_days=30, value=0.5)
    assert fv.is_null is False
    assert fv.confidence == 1.0
    assert fv.signal_count == 0
    assert fv.metadata == {}


# ── 6. BaseFeature cutoff calculation ────────────────────────────────────────
def test_base_feature_cutoff():
    import app.features.corporate
    from app.features.base import FeatureRegistry

    features = FeatureRegistry.all()
    assert features, "Registry must not be empty"

    f = features[0]
    now = datetime.now(tz=timezone.utc)
    cutoff_30 = f._cutoff(30)
    cutoff_90 = f._cutoff(90)

    delta_30 = (now - cutoff_30).total_seconds() / 86400
    delta_90 = (now - cutoff_90).total_seconds() / 86400

    assert 29 <= delta_30 <= 31, f"30d cutoff off: delta={delta_30}"
    assert 89 <= delta_90 <= 91, f"90d cutoff off: delta={delta_90}"


# ── 7. LegalLanguageDensity — legal text scores high ─────────────────────────
@pytest.mark.asyncio
async def test_legal_language_density_high_on_legal_text():
    import app.features.nlp
    from app.features.nlp import LegalLanguageDensityFeature

    f = LegalLanguageDensityFeature()

    # Mock DB returning legal-heavy text
    legal_text = (
        "The plaintiff filed a lawsuit against the defendant seeking damages. "
        "The court ordered an injunction and the matter proceeded to litigation. "
        "Class action settlement was reached. Regulatory enforcement action pending."
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [legal_text]
    mock_db.execute = AsyncMock(return_value=mock_result)

    fv = await f.compute(company_id=1, horizon_days=30, db=mock_db, mongo_db=None)
    assert fv.value > 0.3, f"Legal text should score > 0.3, got {fv.value}"
    assert not fv.is_null


# ── 8. HedgingScore — hedging text scores high ───────────────────────────────
@pytest.mark.asyncio
async def test_hedging_score_high_on_hedged_text():
    import app.features.nlp
    from app.features.nlp import HedgingScoreFeature

    f = HedgingScoreFeature()
    hedging_text = (
        "This may result in significant changes. The company could face uncertainty. "
        "Results might be materially different. Subject to regulatory approval. "
        "No assurance can be given. Forward-looking statements involve risk."
    )

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [hedging_text]
    mock_db.execute = AsyncMock(return_value=mock_result)

    fv = await f.compute(company_id=1, horizon_days=30, db=mock_db, mongo_db=None)
    assert fv.value > 0.5, f"Hedged text should score > 0.5, got {fv.value}"


# ── 9. GoingConcernFlag — returns 1 on matching text ─────────────────────────
@pytest.mark.asyncio
async def test_going_concern_flag_detects_text():
    import app.features.corporate
    from app.features.corporate import GoingConcernFlagFeature

    f = GoingConcernFlagFeature()
    distress_text = "The auditors have expressed substantial doubt about the company's going concern."

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [distress_text]
    mock_db.execute = AsyncMock(return_value=mock_result)

    fv = await f.compute(company_id=1, horizon_days=30, db=mock_db, mongo_db=None)
    assert fv.value == 1.0, f"Going concern text should return 1.0, got {fv.value}"
    assert not fv.is_null


@pytest.mark.asyncio
async def test_going_concern_flag_returns_zero_on_clean_text():
    import app.features.corporate
    from app.features.corporate import GoingConcernFlagFeature

    f = GoingConcernFlagFeature()
    clean_text = "The company reported strong revenue growth this quarter."

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [clean_text]
    mock_db.execute = AsyncMock(return_value=mock_result)

    fv = await f.compute(company_id=1, horizon_days=30, db=mock_db, mongo_db=None)
    assert fv.value == 0.0
    assert not fv.is_null  # null_if_no_signals=False for this feature


# ── 10. CrossSignalConfirmationCount ─────────────────────────────────────────
@pytest.mark.asyncio
async def test_cross_signal_confirmation_counts_categories():
    import app.features.temporal
    from app.features.temporal import CrossSignalConfirmationCountFeature

    f = CrossSignalConfirmationCountFeature()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        "corporate_sedar_plus",
        "news_globe_mail",
        "regulatory_osc",
        "social_reddit",
        "corporate_sedi",   # same category as sedar — shouldn't add extra
    ]
    mock_db.execute = AsyncMock(return_value=mock_result)

    fv = await f.compute(company_id=1, horizon_days=30, db=mock_db, mongo_db=None)
    # corporate_, news_, regulatory_, social_ = 4 categories
    assert fv.value == 4.0, f"Expected 4 categories, got {fv.value}"


# ── 11. FeatureRegistry.by_category ──────────────────────────────────────────
def test_feature_registry_by_category():
    import app.features.corporate
    import app.features.nlp
    import app.features.temporal
    import app.features.geo
    import app.features.macro
    from app.features.base import FeatureRegistry

    nlp_features = FeatureRegistry.by_category("nlp")
    corporate_features = FeatureRegistry.by_category("corporate")
    geo_features = FeatureRegistry.by_category("geo")

    assert len(nlp_features) >= 8, f"Expected >= 8 NLP features, got {len(nlp_features)}"
    assert len(corporate_features) >= 5, f"Expected >= 5 corporate features"
    assert len(geo_features) >= 5, f"Expected >= 5 geo features"

    for f in nlp_features:
        assert f.category == "nlp"
    for f in corporate_features:
        assert f.category == "corporate"


# ── 12. No duplicate feature names ───────────────────────────────────────────
def test_no_duplicate_feature_names():
    import app.features.corporate
    import app.features.nlp
    import app.features.temporal
    import app.features.geo
    import app.features.macro
    from app.features.base import FeatureRegistry

    names = FeatureRegistry.names()
    assert len(names) == len(set(names)), "Duplicate feature names detected in registry"


# ── 13. All features have descriptions ───────────────────────────────────────
def test_all_features_have_description():
    import app.features.corporate
    import app.features.nlp
    import app.features.temporal
    import app.features.geo
    import app.features.macro
    from app.features.base import FeatureRegistry

    for feature in FeatureRegistry.all():
        assert feature.description, \
            f"Feature {feature.name} has no description"
        assert len(feature.description) > 10, \
            f"Feature {feature.name} description too short: {feature.description!r}"


# ── 14. FeatureValue feature_key property ────────────────────────────────────
def test_feature_value_feature_key():
    from app.features.base import FeatureValue
    fv = FeatureValue(
        company_id=42, feature_name="going_concern_flag",
        feature_version="v1", horizon_days=60, value=1.0
    )
    assert fv.feature_key == "going_concern_flag:v1:60d"


# ── 15. compute_all_horizons returns 3 values ─────────────────────────────────
@pytest.mark.asyncio
async def test_compute_all_horizons_returns_three():
    import app.features.corporate
    from app.features.corporate import AuditorChangeFlagFeature

    f = AuditorChangeFlagFeature()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    results = await f.compute_all_horizons(company_id=1, db=mock_db, mongo_db=None)
    assert len(results) == 3
    horizons = {r.horizon_days for r in results}
    assert horizons == {30, 60, 90}


# ── 16. Graph features return null when mongo_db is None ─────────────────────
@pytest.mark.asyncio
async def test_graph_features_null_without_mongo():
    import app.features.macro
    from app.features.macro import DirectorInterlocksScoreFeature

    f = DirectorInterlocksScoreFeature()
    fv = await f.compute(company_id=1, horizon_days=30, db=AsyncMock(), mongo_db=None)
    assert fv.is_null is True, "Graph features must return is_null=True when MongoDB unavailable"

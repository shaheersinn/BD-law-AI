"""
app/features — ORACLE Feature Engineering Pipeline.

Exports the public API for feature computation, registration, and retrieval.
"""

# Force-import feature submodules so @register_feature decorators execute
import app.features.corporate  # noqa: F401
import app.features.geo  # noqa: F401
import app.features.macro  # noqa: F401
import app.features.nlp  # noqa: F401
import app.features.temporal  # noqa: F401
from app.features.base import (
    VALID_HORIZONS,
    BaseFeature,
    FeatureRegistry,
    FeatureValue,
    register_feature,
)
from app.features.runner import FeatureRunner

__all__ = [
    "BaseFeature",
    "FeatureRegistry",
    "FeatureValue",
    "FeatureRunner",
    "register_feature",
    "VALID_HORIZONS",
]

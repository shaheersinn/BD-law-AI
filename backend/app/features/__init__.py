"""
app/features — ORACLE Feature Engineering Pipeline.

Exports the public API for feature computation, registration, and retrieval.
"""

import importlib

# Force-import feature submodules so @register_feature decorators execute
importlib.import_module("app.features.corporate")
importlib.import_module("app.features.geo")
importlib.import_module("app.features.macro")
importlib.import_module("app.features.nlp")
importlib.import_module("app.features.temporal")
from app.features.base import (  # noqa: E402
    VALID_HORIZONS,
    BaseFeature,
    FeatureRegistry,
    FeatureValue,
    register_feature,
)
from app.features.runner import FeatureRunner  # noqa: E402

__all__ = [
    "BaseFeature",
    "FeatureRegistry",
    "FeatureValue",
    "FeatureRunner",
    "register_feature",
    "VALID_HORIZONS",
]

"""
conftest.py for integration tests — mock torch if not installed.

The mock is scoped to session and cleaned up after all integration tests finish.
"""
import sys
import types
from unittest.mock import MagicMock

# Check if real torch is installed
_real_torch_available = "torch" in sys.modules or bool(__import__("importlib").util.find_spec("torch"))

if not _real_torch_available:
    _mock_torch = types.ModuleType("torch")
    _mock_torch.nn = types.ModuleType("torch.nn")  # type: ignore[attr-defined]
    _mock_torch.nn.functional = types.ModuleType("torch.nn.functional")  # type: ignore[attr-defined]
    _mock_torch.nn.Module = type("Module", (), {})  # type: ignore[attr-defined]
    _mock_torch.Tensor = type("Tensor", (), {})  # type: ignore[attr-defined]
    _mock_torch.float32 = "float32"  # type: ignore[attr-defined]
    _mock_torch.no_grad = lambda: MagicMock(__enter__=MagicMock(), __exit__=MagicMock())  # type: ignore[attr-defined]
    _mock_torch_utils = types.ModuleType("torch.utils")
    _mock_torch_utils_data = types.ModuleType("torch.utils.data")
    _mock_torch_utils_data.DataLoader = MagicMock  # type: ignore[attr-defined]
    _mock_torch_utils_data.TensorDataset = MagicMock  # type: ignore[attr-defined]

    # Mark as fake so other test files can detect
    _mock_torch._is_mock = True  # type: ignore[attr-defined]

    sys.modules["torch"] = _mock_torch
    sys.modules["torch.nn"] = _mock_torch.nn
    sys.modules["torch.nn.functional"] = _mock_torch.nn.functional
    sys.modules["torch.utils"] = _mock_torch_utils
    sys.modules["torch.utils.data"] = _mock_torch_utils_data

    # Pre-import ML modules that depend on torch
    import app.ml.orchestrator  # noqa: F401, E402
    import app.ml.anomaly_detector  # noqa: F401, E402
    import app.ml.velocity_scorer  # noqa: F401, E402

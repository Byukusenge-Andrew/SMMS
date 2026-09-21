# Middleware package
import importlib.machinery
from pathlib import Path

_module_path = Path(__file__).resolve().parent.parent / "middleware.py"
if _module_path.exists():
    _loader = importlib.machinery.SourceFileLoader("apps.core._middleware_impl", str(_module_path))
    _core_mod = _loader.load_module()
    RateLimitMiddleware = getattr(_core_mod, "RateLimitMiddleware", None)
    BurstProtectionMiddleware = getattr(_core_mod, "BurstProtectionMiddleware", None)

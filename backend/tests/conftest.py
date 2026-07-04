"""
conftest.py
-----------
Shared pytest configuration for ClinGuard-AI Phase 10 tests.
"""
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `backend.*` imports resolve
# whether pytest is run from the project root or the tests/ directory.
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

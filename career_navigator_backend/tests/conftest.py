"""
Pytest configuration to ensure the application package (src/) is importable.

This adjusts sys.path so `from src.api.main import app` works when tests run
from the container root without an installed package.
"""
import sys
from pathlib import Path

# Compute the backend root that contains the 'src' directory
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Prepend backend root to sys.path if not already present
backend_root_str = str(BACKEND_ROOT)
if backend_root_str not in sys.path:
    sys.path.insert(0, backend_root_str)

# Also ensure that the 'src' directory itself can be found as a top-level package
SRC_DIR = BACKEND_ROOT / "src"
src_dir_str = str(SRC_DIR)
if src_dir_str not in sys.path:
    sys.path.insert(0, src_dir_str)

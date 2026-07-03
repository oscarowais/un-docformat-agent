"""Pytest bootstrap — put the repo root on sys.path so `import app` works
regardless of where pytest is invoked from."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

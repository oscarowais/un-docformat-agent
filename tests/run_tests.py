"""Dependency-free test runner (pytest not required).

Usage: python tests/run_tests.py   (from the repo root)
"""

import inspect
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import test_autofix  # noqa: E402  (same directory)
import test_model  # noqa: E402
import test_rules  # noqa: E402


def main() -> int:
    passed, failed = 0, []
    for module in (test_rules, test_autofix, test_model):
        for name, fn in inspect.getmembers(module, inspect.isfunction):
            if not name.startswith("test_"):
                continue
            try:
                fn()
                passed += 1
            except Exception:
                failed.append((name, traceback.format_exc(limit=3)))

    print(f"{passed} passed, {len(failed)} failed")
    for name, tb in failed:
        print("=" * 70)
        print("FAIL:", name)
        print(tb)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    raise SystemExit(main())

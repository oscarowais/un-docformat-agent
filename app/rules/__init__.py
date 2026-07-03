"""UN formatting rules engine (pure Python — no model/API access required).

Every checker implements `check(doc: DocumentModel) -> list[Finding]` and is
registered in `engine.ALL_CHECKS`. Run them all via `engine.run_checks(doc)`.
"""

from app.rules.engine import run_checks, ALL_CHECKS  # noqa: F401
from app.rules.base import Finding, Severity  # noqa: F401

"""
ACE LayerPolicy — Architectural Capability Boundary Tests.

Tests both positive (valid dependency paths) and negative (forbidden imports)
scenarios to prove that LayerPolicy deterministically catches and blocks violations.
"""
import ast
import os
import subprocess
import sys
import tempfile
import pytest

from ace.src.contracts.finding import Severity
from ace.src.contracts.rule import RuleContext
from ace.src.governance.policies.layer_policy import (
    LayerDependencyRule,
    LayerPolicy,
    _extract_imports,
    _file_belongs_to_capability,
    CAPABILITIES,
)


class MockArchitectureModel:
    def __init__(self, ast_cache: dict[str, ast.AST]):
        self._ast_cache = ast_cache
        self._context = self

    @property
    def _capabilities(self):
        class MockASTProvider:
            capability_type = "ast"
            def __init__(self, cache):
                self._cache = cache
            def get_data(self):
                return self._cache
        return {"ast": MockASTProvider(self._ast_cache)}


def _make_ast(code: str) -> ast.AST:
    return ast.parse(code)


# ---------------------------------------------------------------------------
# Test 1: Positive — Clean Architecture Passes
# ---------------------------------------------------------------------------

def test_clean_architecture_passes():
    rule = LayerDependencyRule()
    clean_cache = {
        "backend/app/models/article.py": _make_ast(
            "from sqlalchemy import Column, Integer, String\nfrom app.models.base import Base\n"
        ),
        "backend/app/schemas/news.py": _make_ast(
            "from pydantic import BaseModel\nfrom app.schemas.common import Pagination\n"
        ),
        "backend/app/services/article_service.py": _make_ast(
            "from app.models.article import ProcessedArticle\nfrom app.schemas.news import ArticleCard\n"
        ),
        "backend/app/api/v1/routes/news.py": _make_ast(
            "from app.services.article_service import ArticleService\nfrom app.models.article import ArticleReadModel\n"
        ),
    }
    context = RuleContext(architecture=MockArchitectureModel(clean_cache))
    findings = rule.evaluate(context)

    violations = [f for f in findings if f.severity == Severity.VIOLATION]
    assert len(violations) == 0
    assert any(f.severity == Severity.INFO for f in findings)


# ---------------------------------------------------------------------------
# Test 2: Negative — Domain importing from Services (Forbidden)
# ---------------------------------------------------------------------------

def test_domain_importing_service_triggers_violation():
    rule = LayerDependencyRule()
    dirty_cache = {
        "backend/app/models/user.py": _make_ast(
            "from app.services.personalization_service import PersonalizationService\n"
        ),
    }
    context = RuleContext(architecture=MockArchitectureModel(dirty_cache))
    findings = rule.evaluate(context)

    violations = [f for f in findings if f.severity == Severity.VIOLATION]
    assert len(violations) == 1
    assert "app.services." in violations[0].message
    assert "domain" in violations[0].message.lower()


# ---------------------------------------------------------------------------
# Test 3: Negative — Domain importing from Database/Redis (Forbidden)
# ---------------------------------------------------------------------------

def test_domain_importing_infrastructure_triggers_violation():
    rule = LayerDependencyRule()
    dirty_cache = {
        "backend/app/models/article.py": _make_ast(
            "from app.core.database import async_engine\n"
        ),
        "backend/app/schemas/feed.py": _make_ast(
            "from app.core.redis import get_redis_client\n"
        ),
    }
    context = RuleContext(architecture=MockArchitectureModel(dirty_cache))
    findings = rule.evaluate(context)

    violations = [f for f in findings if f.severity == Severity.VIOLATION]
    assert len(violations) == 2


# ---------------------------------------------------------------------------
# Test 4: Negative — Application importing from API routes (Forbidden)
# ---------------------------------------------------------------------------

def test_application_importing_interface_triggers_violation():
    rule = LayerDependencyRule()
    dirty_cache = {
        "backend/app/services/cache_service.py": _make_ast(
            "from app.api.v1.routes.news import _in_memory_homepage_cache\n"
        ),
    }
    context = RuleContext(architecture=MockArchitectureModel(dirty_cache))
    findings = rule.evaluate(context)

    violations = [f for f in findings if f.severity == Severity.VIOLATION]
    assert len(violations) == 1
    assert "app.api." in violations[0].message
    assert "application" in violations[0].message.lower()


# ---------------------------------------------------------------------------
# Test 5: Positive — Application importing Domain & Infrastructure is Allowed
# ---------------------------------------------------------------------------

def test_application_importing_domain_and_infra_allowed():
    rule = LayerDependencyRule()
    allowed_cache = {
        "backend/app/services/distribution_service.py": _make_ast(
            "from app.models.distribution import DistributionJob\nfrom app.core.database import AsyncSessionLocal\nfrom app.core.redis import get_redis_client\n"
        ),
    }
    context = RuleContext(architecture=MockArchitectureModel(allowed_cache))
    findings = rule.evaluate(context)

    violations = [f for f in findings if f.severity == Severity.VIOLATION]
    assert len(violations) == 0


# ---------------------------------------------------------------------------
# Test 6: CLI Integration & Exit Code Contract Verification
# ---------------------------------------------------------------------------

def test_ace_cli_check_command_passes():
    """Verify that running python -m ace.src.cli check in the repo root exits with code 0."""
    result = subprocess.run(
        [sys.executable, "-m", "ace.src.cli", "check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"ACE check failed with output:\n{result.stdout}\n{result.stderr}"
    assert "[PASS]" in result.stdout

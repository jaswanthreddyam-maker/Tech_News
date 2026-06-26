from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import ast
import os
import json
import subprocess

class ASTProvider:
    """Parses and caches Python Abstract Syntax Trees for the repository."""
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self._cache: Dict[str, ast.AST] = {}
        self._preload_cache()

    def _preload_cache(self):
        # Scan backend/app for python files
        target_dir = os.path.join(self.root_dir, "backend", "app")
        if not os.path.exists(target_dir):
            return
            
        for dirpath, _, filenames in os.walk(target_dir):
            for file in filenames:
                if file.endswith(".py"):
                    full_path = os.path.join(dirpath, file)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            self._cache[rel_path] = ast.parse(f.read(), filename=full_path)
                    except Exception:
                        pass # Ignore parsing errors for now

    def get_ast(self, file_path: str) -> ast.AST:
        return self._cache.get(file_path)

    def find_classes_inheriting(self, base_class_name: str) -> List[tuple[str, ast.ClassDef]]:
        results = []
        for file_path, tree in self._cache.items():
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == base_class_name:
                            results.append((file_path, node))
        return results

class MarkdownProvider:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self._cache: Dict[str, str] = {}

    def get_markdown(self, file_path: str) -> str:
        return ""

class OpenAPIProvider:
    def __init__(self, spec_path: str):
        self.spec_path = spec_path
        self._spec: Optional[Dict[str, Any]] = None

    def get_spec(self) -> Dict[str, Any]:
        return {}

class GitProvider:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir

    def get_current_commit(self) -> str:
        return "1.0.0"

    def get_changed_files(self) -> List[str]:
        return []

@dataclass(frozen=True)
class RepositoryContext:
    root_dir: str
    ast: ASTProvider
    docs: MarkdownProvider
    openapi: OpenAPIProvider
    git: GitProvider

def build_context(root_dir: str) -> RepositoryContext:
    return RepositoryContext(
        root_dir=root_dir,
        ast=ASTProvider(root_dir),
        docs=MarkdownProvider(root_dir),
        openapi=OpenAPIProvider(os.path.join(root_dir, "openapi.json")),
        git=GitProvider(root_dir)
    )

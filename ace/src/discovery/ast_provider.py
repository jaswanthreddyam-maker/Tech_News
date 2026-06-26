import ast
import os
from typing import Dict, Any, List
from ace.src.contracts.capability import CapabilityProvider

class ASTProvider(CapabilityProvider):
    """
    Parses Python files into Abstract Syntax Trees.
    Implements the Capability public contract.
    """
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self._cache: Dict[str, ast.AST] = {}
        self._preload_cache()

    @property
    def capability_type(self) -> str:
        return "ast"

    def discover(self) -> Dict[str, ast.AST]:
        return self._cache

    def version(self) -> str:
        return "1.0.0"

    def _preload_cache(self):
        target_dir = os.path.join(self.root_dir, "backend", "app")
        if not os.path.exists(target_dir):
            return
            
        for dirpath, _, filenames in os.walk(target_dir):
            for file in filenames:
                if file.endswith(".py"):
                    full_path = os.path.join(dirpath, file)
                    rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            self._cache[rel_path] = ast.parse(f.read(), filename=full_path)
                    except Exception:
                        pass

    def get_data(self) -> Dict[str, ast.AST]:
        return self._cache

from pathlib import Path
import sys
import pytest
from tools.cookbook.inventory import inventory_python_code, inventory_python_tree

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_inventory_extracts_functions_classes_async():
    code = """
class SafeRunner:
    def run_sync(self, cmd: str) -> int:
        return 0

    async def run_async(self, timeout: float = 1.0) -> bool:
        return True

def standalone_helper(x: int) -> int:
    return x * 2

async def async_dispatcher(action: str) -> None:
    pass
"""
    symbols = inventory_python_code(code, "test_file.py")
    names = {s.symbol for s in symbols}
    types = {s.symbol: s.type for s in symbols}

    assert "SafeRunner" in names
    assert types["SafeRunner"] == "class"

    assert "SafeRunner.run_sync" in names
    assert types["SafeRunner.run_sync"] == "method"

    assert "SafeRunner.run_async" in names
    assert types["SafeRunner.run_async"] == "async_method"

    assert "standalone_helper" in names
    assert types["standalone_helper"] == "function"

    assert "async_dispatcher" in names
    assert types["async_dispatcher"] == "async_function"


def test_inventory_never_imports_modules():
    initial_modules = set(sys.modules.keys())
    inventory_python_tree(REPO_ROOT / "app")
    new_modules = set(sys.modules.keys()) - initial_modules
    app_modules = [m for m in new_modules if m.startswith("app")]
    assert app_modules == [], f"Inventory must use AST only, but imported: {app_modules}"


def test_inventory_scans_app_directory():
    symbols = inventory_python_tree(REPO_ROOT / "app")
    assert len(symbols) > 20
    symbol_names = [s.symbol for s in symbols]
    assert any("ActionDispatcher" in s for s in symbol_names)
    assert any("PolicyEngine" in s for s in symbol_names)

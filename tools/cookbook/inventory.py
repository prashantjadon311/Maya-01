import ast
from pathlib import Path
from tools.cookbook.model import SymbolItem


class SymbolVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.symbols: list[SymbolItem] = []
        self.current_class: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef):
        class_name = node.name
        self.symbols.append(
            SymbolItem(
                symbol=class_name,
                file=self.file_path,
                type="class",
                status="KEEP",
            )
        )
        prev_class = self.current_class
        self.current_class = class_name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        fn_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
        sym_type = "method" if self.current_class else "function"

        # extract callees from ast.Call
        callees = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    callees.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    callees.append(child.func.attr)

        self.symbols.append(
            SymbolItem(
                symbol=fn_name,
                file=self.file_path,
                type=sym_type,
                status="KEEP",
                callees=sorted(list(set(callees))),
            )
        )
        # We don't visit nested function defs under a function as methods
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit(child)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        fn_name = f"{self.current_class}.{node.name}" if self.current_class else node.name
        sym_type = "async_method" if self.current_class else "async_function"

        callees = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    callees.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    callees.append(child.func.attr)

        self.symbols.append(
            SymbolItem(
                symbol=fn_name,
                file=self.file_path,
                type=sym_type,
                status="KEEP",
                callees=sorted(list(set(callees))),
            )
        )
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.visit(child)


def inventory_python_code(code: str, file_path: str) -> list[SymbolItem]:
    """Parse python code string using AST only and extract symbol inventory."""
    tree = ast.parse(code, filename=file_path)
    visitor = SymbolVisitor(file_path)
    visitor.visit(tree)
    return visitor.symbols


def inventory_python_tree(root: Path) -> list[SymbolItem]:
    """Walk directory tree and extract AST symbol inventory for all Python files."""
    all_symbols: list[SymbolItem] = []
    py_files = sorted(root.rglob("*.py"))

    for py_file in py_files:
        # Ignore cache or hidden dirs
        if any(part.startswith(".") or part == "__pycache__" for part in py_file.parts):
            continue
        try:
            code = py_file.read_text(encoding="utf-8")
            rel_path = str(py_file.as_posix())
            # make path relative to Maya root if possible
            if "Maya/" in rel_path:
                rel_path = rel_path.split("Maya/", 1)[1]
            symbols = inventory_python_code(code, rel_path)
            all_symbols.extend(symbols)
        except Exception as e:
            print(f"Warning: could not parse {py_file}: {e}")

    # Cross-reference callers
    callee_to_callers = {}
    for sym in all_symbols:
        for callee in sym.callees:
            callee_to_callers.setdefault(callee, set()).add(sym.symbol)

    for sym in all_symbols:
        simple_name = sym.symbol.split(".")[-1]
        callers = callee_to_callers.get(simple_name, set())
        sym.callers = sorted(list(callers))

    return all_symbols

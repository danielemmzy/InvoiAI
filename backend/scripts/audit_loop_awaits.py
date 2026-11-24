"""Report loops that await inside a backend module (candidate N+1 sites)."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("app")

DB_HINTS = (
    "execute",
    "run_db",
    "gather_queries",
    "table",
    "repository",
    "_repo",
    "fetch",
    "query",
    "supabase",
    "db.",
    "list_",
    "get_",
)


def names_in(node: ast.AST) -> list[str]:
    out: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Await):
            target = child.value
            if isinstance(target, ast.Call):
                func = target.func
                if isinstance(func, ast.Attribute):
                    out.append(func.attr)
                elif isinstance(func, ast.Name):
                    out.append(func.id)
    return out


def looks_like_db(label: str) -> bool:
    low = label.lower()
    return any(hint in low for hint in DB_HINTS)


results = []
unparsed: list[tuple[str, str]] = []
for path in sorted(ROOT.rglob("*.py")):
    if any(part in {"__pycache__", "tests"} for part in path.parts):
        continue
    try:
        # utf-8-sig tolerates a leading byte-order mark; several backend
        # modules were edited with a BOM and were silently skipped before.
        tree = ast.parse(path.read_text(encoding="utf-8-sig", errors="replace"))
    except SyntaxError as exc:
        unparsed.append((str(path).replace("\\", "/"), f"line {exc.lineno}: {exc.msg}"))
        continue

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.funcs: list[str] = []

        def visit_FunctionDef(self, node):
            self.funcs.append(node.name)
            self.generic_visit(node)
            self.funcs.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_For(self, node):
            self._loop(node)

        visit_AsyncFor = visit_For

        def _loop(self, node):
            awaited = names_in(node)
            if awaited:
                func = self.funcs[-1] if self.funcs else "<module>"
                calls = [a for a in awaited if looks_like_db(a)]
                if calls or awaited:
                    results.append(
                        {
                            "file": str(path).replace("\\", "/"),
                            "function": func,
                            "line": node.lineno,
                            "awaits": sorted(set(awaited)),
                            "db_like": sorted(set(calls)),
                        }
                    )
            self.generic_visit(node)

    Visitor().visit(tree)

results.sort(key=lambda item: (item["file"], item["line"]))
for item in results:
    print(
        f"{item['file']}:{item['line']} {item['function']} -> "
        f"{', '.join(item['awaits'])}"
    )
if unparsed:
    print("\nUNPARSED FILES (excluded from the audit):")
    for file, detail in unparsed:
        print(f"  {file} ({detail})")
print(
    f"\n{len(results)} loop(s) with await; {len(unparsed)} file(s) could not be parsed",
    file=sys.stderr,
)

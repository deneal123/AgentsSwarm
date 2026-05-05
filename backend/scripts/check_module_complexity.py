from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Thresholds:
    max_lines_per_file: int
    max_function_length: int
    max_cyclomatic_complexity: int
    max_import_fan_out: int
    max_import_fan_in: int


class CyclomaticVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.complexity = 1

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.IfExp,
                ast.ExceptHandler,
                ast.With,
                ast.AsyncWith,
                ast.Assert,
                ast.Try,
            ),
        ):
            self.complexity += 1
        if isinstance(node, ast.BoolOp):
            self.complexity += max(len(node.values) - 1, 0)
        if isinstance(node, ast.Match):
            self.complexity += len(node.cases)
        super().generic_visit(node)


class QualityError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="service")
    parser.add_argument("--critical", nargs="+", default=["service/services", "service/agents"])
    parser.add_argument("--max-lines-per-file", type=int, default=750)
    parser.add_argument("--max-function-length", type=int, default=250)
    parser.add_argument("--max-cyclomatic-complexity", type=int, default=70)
    parser.add_argument("--max-import-fan-out", type=int, default=120)
    parser.add_argument("--max-import-fan-in", type=int, default=160)
    return parser.parse_args()


def module_name(root: Path, file_path: Path) -> str:
    return ".".join(file_path.relative_to(root).with_suffix("").parts)


def imported_module(base_module: str, node_module: str | None, level: int) -> str | None:
    if level == 0:
        return node_module
    parts = base_module.split(".")
    if len(parts) < level:
        return None
    prefix = parts[: len(parts) - level]
    if node_module:
        prefix.extend(node_module.split("."))
    return ".".join(prefix)


def collect_python_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def function_nodes(tree: ast.AST) -> list[ast.AST]:
    return [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def evaluate(root: Path, critical_dirs: list[Path], thresholds: Thresholds) -> None:
    files = collect_python_files(root)
    violations: list[str] = []
    import_graph: dict[str, set[str]] = defaultdict(set)
    critical_modules: set[str] = set()

    for file_path in files:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        module = module_name(root, file_path)

        if any(file_path.is_relative_to(critical_dir) for critical_dir in critical_dirs):
            critical_modules.add(module)

        lines = len(source.splitlines())
        if lines > thresholds.max_lines_per_file:
            violations.append(
                f"{file_path}: lines={lines} exceeds max_lines_per_file={thresholds.max_lines_per_file}"
            )

        for func in function_nodes(tree):
            func_len = (func.end_lineno or func.lineno) - func.lineno + 1
            if func_len > thresholds.max_function_length:
                violations.append(
                    f"{file_path}:{func.lineno} {func.name} length={func_len} exceeds "
                    f"max_function_length={thresholds.max_function_length}"
                )
            visitor = CyclomaticVisitor()
            visitor.visit(func)
            if visitor.complexity > thresholds.max_cyclomatic_complexity:
                violations.append(
                    f"{file_path}:{func.lineno} {func.name} complexity={visitor.complexity} exceeds "
                    f"max_cyclomatic_complexity={thresholds.max_cyclomatic_complexity}"
                )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_graph[module].add(alias.name)
            if isinstance(node, ast.ImportFrom):
                imported = imported_module(module, node.module, node.level)
                if imported:
                    import_graph[module].add(imported)

    fan_in = Counter()
    fan_out = {module: len(imports) for module, imports in import_graph.items()}

    for module, imports in import_graph.items():
        for imported in imports:
            if imported in critical_modules:
                fan_in[imported] += 1

    for module in critical_modules:
        out = fan_out.get(module, 0)
        if out > thresholds.max_import_fan_out:
            violations.append(
                f"{module}: fan_out={out} exceeds max_import_fan_out={thresholds.max_import_fan_out}"
            )
        fin = fan_in.get(module, 0)
        if fin > thresholds.max_import_fan_in:
            violations.append(
                f"{module}: fan_in={fin} exceeds max_import_fan_in={thresholds.max_import_fan_in}"
            )

    if violations:
        raise QualityError("\n".join(sorted(violations)))


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    critical_dirs = [Path(path).resolve() for path in args.critical]
    thresholds = Thresholds(
        max_lines_per_file=args.max_lines_per_file,
        max_function_length=args.max_function_length,
        max_cyclomatic_complexity=args.max_cyclomatic_complexity,
        max_import_fan_out=args.max_import_fan_out,
        max_import_fan_in=args.max_import_fan_in,
    )
    evaluate(root=root, critical_dirs=critical_dirs, thresholds=thresholds)


if __name__ == "__main__":
    main()

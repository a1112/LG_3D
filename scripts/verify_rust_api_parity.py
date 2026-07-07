#!/usr/bin/env python3
"""Verify API route parity between legacy Python API service and Rust API service."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
PY_GLOBS = (
    "app/Server/api/**/*.py",
    "app/Communication/*.py",
    "app/CapTrue/*.py",
    "app/plcServer/*.py",
    "app/algorithm_runtime/**/*.py",
    "app/algorithm_runtime_2D/*.py",
)
RUST_ROUTE_FILE = ROOT / "app/Server/rust_api_service/src/routes.rs"
DEFAULT_FRONTEND_SERVICE_GLOBS = (
    "app/UI/MotionStudioWeb/src/services/api.ts",
)

Method = str
PathWithMethod = Tuple[Method, str]


def normalize_path(path: str) -> str:
    """Normalize typed/splat parameters for method+path comparison."""
    path = path.strip()
    path = re.sub(r"\{[^{}:]+\}", "{param}", path)
    path = re.sub(r"\{[^{}:]+:[^{}]+\}", "{param}", path)
    path = re.sub(r"\{\*[^{}]+\}", "{param}", path)
    path = re.sub(r"\([^()]+\)", "{param}", path)
    if re.fullmatch(r"/static/[^{}?#]+", path):
        path = "/static/{param}"
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")
    return path


def _add_route(routes: Set[PathWithMethod], method: str, path: str) -> None:
    normalized = normalize_path(path)
    routes.add((method.upper(), normalized))
    if path.endswith("/") and len(path) > 1:
        routes.add((method.upper(), path.rstrip("/")))


def parse_python_routes() -> Set[PathWithMethod]:
    routes: Set[PathWithMethod] = set()
    for pattern in PY_GLOBS:
        for path in ROOT.glob(pattern):
            text = path.read_text(encoding="utf-8", errors="ignore")
            routes.update(_parse_fastapi_defaults(text))
            for match in re.finditer(
                r'@(router|app)\.(get|post|put|delete|patch|options|head)\(\s*["\'](?P<route>/[^"\']+)["\']',
                text,
            ):
                _add_route(routes, match.group(2), match.group("route"))

            for match in re.finditer(
                r'@(router|app)\.websocket\(\s*["\'](?P<route>/[^"\']+)["\']',
                text,
            ):
                _add_route(routes, "GET", match.group("route"))

            for match in re.finditer(
                r"router\.api\.(get|post|put|delete|patch|options|head)\(\s*['\"](?P<route>/[^'\"]+)['\"]",
                text,
            ):
                _add_route(routes, match.group(1), match.group("route"))

            for match in re.finditer(
                r'@(router|app)\.\(get|post|put|delete|patch|options|head\)', text
            ):
                _ = match

            for match in re.finditer(
                r'add_api_route\(\s*["\'](?P<route>/[^"\']+)["\']\s*,\s*[^,]+,\s*methods=\[(?P<methods>[^\]]+)\]',
                text,
            ):
                route = match.group("route")
                methods = (item.strip().strip('\'"') for item in match.group("methods").split(","))
                for item in methods:
                    if item:
                        _add_route(routes, item, route)
    return routes


def _parse_fastapi_defaults(text: str) -> Set[PathWithMethod]:
    routes: Set[PathWithMethod] = set()
    for app_name, args in _iter_fastapi_app_instances(text):
        if app_name is None:
            continue

        docs_url, redoc_url, openapi_url = _extract_fastapi_urls(args)
        if docs_url is not None:
            _add_route(routes, "GET", docs_url)
        if redoc_url is not None:
            _add_route(routes, "GET", redoc_url)
        if openapi_url is not None:
            _add_route(routes, "GET", openapi_url)

    for match in re.finditer(
        rf"{_python_identifier()}\.mount\(\s*(?P<path>\"[^\"]+\"|'[^']+'|`[^`]+`)",
        text,
    ):
        mount_path = match.group("path")[1:-1]
        if mount_path.startswith("/"):
            _add_route(routes, "GET", f"{mount_path}/{{param}}")

    if "swagger_ui_oauth2_redirect_url" in text:
        _add_route(routes, "GET", "/docs/oauth2-redirect")

    return routes


def _python_identifier() -> str:
    return r"[A-Za-z_][A-Za-z0-9_]*"


def _iter_fastapi_app_instances(text: str) -> List[tuple[str, str]]:
    instances = []
    pattern = re.compile(
        rf"(?P<name>{_python_identifier()})\s*=\s*FastAPI\((?P<args>.*?)\)",
        re.S,
    )
    for match in pattern.finditer(text):
        args = match.group("args")
        if args is None:
            continue
        instances.append((match.group("name"), args))
    return instances


def _extract_fastapi_urls(args: str) -> Tuple[str | None, str | None, str | None]:
    def _extract_url_arg(name: str, default: str | None) -> str | None:
        regex = re.compile(
            rf"{re.escape(name)}\s*=\s*(?P<value>[^,\\)]+)",
            re.I,
        )
        match = regex.search(args)
        if not match:
            return default
        value = match.group("value").strip()
        if value in {"None", "False", "false"}:
            return None
        if value in {"NoneType", ""}:
            return None
        if re.fullmatch(r"[\"'`]([^\"'`]+)[\"'`]", value):
            return value[1:-1]
        if value.startswith("app.openapi_url"):
            # avoid recursively referencing unresolved app name at parse time
            return "/openapi.json"
        return default

    docs_url = _extract_url_arg("docs_url", "/docs")
    redoc_url = _extract_url_arg("redoc_url", "/redoc")
    openapi_url = _extract_url_arg("openapi_url", "/openapi.json")
    return docs_url, redoc_url, openapi_url


def parse_rust_routes() -> Set[PathWithMethod]:
    text = RUST_ROUTE_FILE.read_text(encoding="utf-8", errors="ignore")
    routes: Set[PathWithMethod] = set()

    index = 0
    while True:
        start = text.find(".route(", index)
        if start < 0:
            break

        open_index = start + len(".route(")
        close_index = _find_matching_bracket(text, open_index, "(", ")")
        if close_index < 0:
            break

        block = text[open_index:close_index]
        index = close_index + 1

        route_match = re.match(r'\s*["\'](?P<path>/[^"\']+)["\']\s*,\s*(?P<body>.+)', block, re.S)
        if not route_match:
            continue

        route = route_match.group("path")
        body = route_match.group("body")
        methods = re.findall(r"\b(get|post|put|delete|patch|options|head)\(", body)
        for method in methods:
            _add_route(routes, method, route)

    for match in re.finditer(
        r'\.(get|post|put|delete|patch|options|head)\(\s*["\'](?P<path>/[^"\']+)["\']\s*,',
        text,
    ):
        _add_route(routes, match.group(1), match.group("path"))

    return routes


def _find_matching_bracket(text: str, open_index: int, open_ch: str, close_ch: str) -> int:
    if open_index >= len(text):
        return -1

    if text[open_index] == open_ch:
        depth = 1
        index = open_index + 1
    else:
        depth = 1
        index = open_index

    in_str: str | None = None
    escaped = False
    while index < len(text):
        ch = text[index]
        if escaped:
            escaped = False
            index += 1
            continue

        if in_str is not None:
            if ch == "\\":
                escaped = True
            elif ch == in_str:
                in_str = None
            index += 1
            continue

        if ch == "\\":
            escaped = True
            index += 1
            continue
        if ch in {'"', "'", "`"}:
            in_str = ch
            index += 1
            continue
        if ch == "/" and index + 1 < len(text):
            if text[index + 1] == "/":
                index += 2
                while index < len(text) and text[index] not in "\r\n":
                    index += 1
                continue
            if text[index + 1] == "*":
                index += 2
                while index + 1 < len(text) and not (text[index] == "*" and text[index + 1] == "/"):
                    index += 1
                index += 2
                continue

        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return -1


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _strip_comments(text: str) -> str:
    return re.sub(r"(?s)/\*.*?\*/|//[^\n]*\n", "", text)


def _normalize_frontend_path(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    # keep only path part
    value = value.split("?", 1)[0]
    value = value.split("#", 1)[0]
    if not value.startswith("/"):
        return None
    if value in {"/", "/api", "/api/"}:
        return None
    if value.startswith("/image") or value == "/image-api":
        return None
    return normalize_path(value)


def _unquote_template(raw: str) -> str:
    if raw.startswith("`") and raw.endswith("`"):
        return raw[1:-1]
    if raw.startswith(('"', "'")) and raw.endswith(raw[0]):
        quote = raw[0]
        return raw[1:-1]
    return raw


def _replace_params(raw: str) -> str:
    return re.sub(r"\$\{[^{}]+\}", "{param}", raw)


def _split_top_level_args(text: str) -> List[str]:
    args: List[str] = []
    depth = 0
    in_str: str | None = None
    escaped = False
    start = 0

    index = 0
    while index < len(text):
        ch = text[index]
        if escaped:
            escaped = False
            index += 1
            continue

        if in_str is not None:
            if ch == "\\":
                escaped = True
            elif ch == in_str:
                in_str = None
            index += 1
            continue

        if ch == "\\":
            escaped = True
            index += 1
            continue

        if ch in {'"', "'", "`"}:
            in_str = ch
            index += 1
            continue

        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth > 0:
                depth -= 1
        elif ch == "," and depth == 0:
            args.append(text[start:index].strip())
            start = index + 1
        index += 1

    args.append(text[start:].strip())
    return [arg for arg in args if arg]


def _extract_expression_from_return(body: str) -> str | None:
    for match in re.finditer(r"\breturn\b", body):
        cursor = match.end()
        depth = 0
        in_str: str | None = None
        escaped = False
        expr_chars = []
        while cursor < len(body):
            ch = body[cursor]
            if escaped:
                escaped = False
                expr_chars.append(ch)
                cursor += 1
                continue
            if in_str is not None:
                if ch == "\\":
                    escaped = True
                elif ch == in_str:
                    in_str = None
                expr_chars.append(ch)
                cursor += 1
                continue

            if ch == "\\":
                escaped = True
                expr_chars.append(ch)
                cursor += 1
                continue
            if ch in {'"', "'", "`"}:
                in_str = ch
                expr_chars.append(ch)
                cursor += 1
                continue
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth > 0:
                    depth -= 1
            elif ch in {";", "}", "\n", "\r"} and depth == 0:
                break
            expr_chars.append(ch)
            cursor += 1

        expr = "".join(expr_chars).strip()
        if expr:
            return expr
    return None


def _collect_builder_paths(text: str) -> dict[str, str]:
    builder_paths: dict[str, str] = {}

    function_pat = re.compile(r"(?:export\s+)?function\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)
    for match in function_pat.finditer(text):
        name = match.group("name")
        open_paren = text.find("(", match.end() - 1)
        if open_paren < 0:
            continue
        close_paren = _find_matching_bracket(text, open_paren, "(", ")")
        if close_paren < 0:
            continue
        brace_pos = text.find("{", close_paren + 1)
        if brace_pos < 0:
            continue
        close_brace = _find_matching_bracket(text, brace_pos, "{", "}")
        if close_brace < 0:
            continue
        body = text[brace_pos + 1 : close_brace]
        expr = _extract_expression_from_return(body)
        if expr:
            builder_paths[name] = expr

    const_fn_pat = re.compile(
        r"(?:export\s+)?const\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\([^\)]*\)\s*=>\s*{",
        re.M,
    )
    for match in const_fn_pat.finditer(text):
        name = match.group("name")
        brace_pos = text.find("{", match.end() - 1)
        if brace_pos < 0:
            continue
        close_brace = _find_matching_bracket(text, brace_pos, "{", "}")
        if close_brace < 0:
            continue
        body = text[brace_pos + 1 : close_brace]
        expr = _extract_expression_from_return(body)
        if expr:
            builder_paths[name] = expr

    const_inline_pat = re.compile(
        r"(?:export\s+)?const\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\([^\)]*\)\s*=>\s*(?P<expr>[^\n;]+);",
        re.M,
    )
    for match in const_inline_pat.finditer(text):
        builder_paths[match.group("name")] = match.group("expr").strip()

    return builder_paths


def _resolve_frontend_path(
    expression: str,
    builder_paths: dict[str, str],
    seen: set[str],
) -> str | None:
    expr = expression.strip()
    if not expr:
        return None

    expr = re.sub(r"\s+", "", expr)
    if expr in ("\"", "'", "`"):
        return None

    if expr.startswith("`") and expr.endswith("`"):
        return _normalize_frontend_path(_replace_params(_unquote_template(expr)))
    if expr.startswith(("'", '"')) and expr.endswith(expr[0]):
        return _normalize_frontend_path(_replace_params(_unquote_template(expr)))

    # /foo/{$} (template-like expression without backticks)
    if expr.startswith("/") or expr.startswith("`/"):
        return _normalize_frontend_path(_replace_params(expr))

    # joinBaseUrl(baseUrl, path)
    if expr.startswith("joinBaseUrl("):
        open_pos = expr.find("(")
        close_pos = _find_matching_bracket(expr, open_pos, "(", ")")
        if close_pos < 0:
            return None
        args = _split_top_level_args(expr[open_pos + 1 : close_pos])
        if len(args) >= 2:
            return _resolve_frontend_path(args[1], builder_paths, seen)
        return None

    if expr.startswith("appendOptionalParams("):
        open_pos = expr.find("(")
        close_pos = _find_matching_bracket(expr, open_pos, "(", ")")
        if close_pos < 0:
            return None
        args = _split_top_level_args(expr[open_pos + 1 : close_pos])
        if not args:
            return None
        return _resolve_frontend_path(args[0], builder_paths, seen)

    if expr.startswith("normalizeSurfaceKey("):
        return None

    call = re.match(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(", expr)
    if call:
        name = call.group("name")
        if name in seen:
            return None
        builder_expr = builder_paths.get(name)
        if builder_expr is None:
            return None
        seen.add(name)
        resolved = _resolve_frontend_path(builder_expr, builder_paths, seen)
        seen.remove(name)
        return resolved

    return None


def parse_frontend_routes(
    globs: Tuple[str, ...] = DEFAULT_FRONTEND_SERVICE_GLOBS,
) -> Set[PathWithMethod]:
    routes: Set[PathWithMethod] = set()
    for glob in globs:
        for service_file in ROOT.glob(glob):
            if not service_file.is_file():
                continue
            text = _read_text(service_file)
            cleaned = _strip_comments(text)
            builder_paths = _collect_builder_paths(cleaned)
            for match in re.finditer(
                r"apiClient\.(get|post|put|delete|patch|options|head)(?:<[^>]*>)?\s*\(",
                cleaned,
            ):
                method = match.group(1)
                open_pos = match.end() - 1
                close_pos = _find_matching_bracket(cleaned, open_pos, "(", ")")
                if close_pos < 0:
                    continue
                arguments = cleaned[open_pos + 1 : close_pos]
                args = _split_top_level_args(arguments)
                if not args:
                    continue
                path = _resolve_frontend_path(args[0], builder_paths, set())
                if path:
                    _add_route(routes, method, path)
    return routes


def diff_routes(
    py_routes: Iterable[PathWithMethod], rs_routes: Iterable[PathWithMethod]
) -> Tuple[List[PathWithMethod], List[PathWithMethod]]:
    py_set = set(py_routes)
    rs_set = set(rs_routes)
    return sorted(rs_set - py_set), sorted(py_set - rs_set)


def diff_frontend_routes(
    frontend_routes: Set[PathWithMethod], rs_routes: Set[PathWithMethod]
) -> Tuple[List[PathWithMethod], int]:
    matched = len(frontend_routes & rs_routes)
    only_in_frontend = sorted(frontend_routes - rs_routes)
    return only_in_frontend, matched


@dataclass
class Report:
    py_count: int
    rs_count: int
    only_in_py: List[PathWithMethod]
    only_in_rs: List[PathWithMethod]

    def as_markdown(self) -> str:
        lines = [
            f"Python routes: {self.py_count}",
            f"Rust routes: {self.rs_count}",
            "",
            "## Only in Python",
        ]
        lines.extend([f"- {method} {path}" for method, path in self.only_in_py] or ["- (none)"])
        lines.extend(["", "## Only in Rust"])
        lines.extend([f"- {method} {path}" for method, path in self.only_in_rs] or ["- (none)"])
        return "\n".join(lines)


@dataclass
class FrontendReport:
    frontend_count: int
    rs_count: int
    matched_count: int
    only_in_frontend: List[PathWithMethod]

    def as_markdown(self) -> str:
        lines = [
            f"Frontend paths (method-aware): {self.frontend_count}",
            f"Rust paths: {self.rs_count}",
            f"Matched: {self.matched_count}",
            "",
            "## Only in Frontend (not in Rust)",
        ]
        lines.extend([f"- {method} {path}" for method, path in self.only_in_frontend] or ["- (none)"])
        return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print JSON instead of markdown")
    parser.add_argument("--frontend", action="store_true", help="Also compare frontend service paths")
    parser.add_argument(
        "--frontend-service-glob",
        action="append",
        default=[],
        help="Glob pattern for frontend service files. Default: app/UI/MotionStudioWeb/src/services/api.ts",
    )
    args = parser.parse_args()

    py_routes = parse_python_routes()
    rs_routes = parse_rust_routes()
    rs_only, py_only = diff_routes(py_routes, rs_routes)

    frontend_only: List[PathWithMethod] = []
    frontend_count = 0
    frontend_matched = 0
    if args.frontend:
        frontend_patterns = (
            tuple(args.frontend_service_glob)
            if args.frontend_service_glob
            else DEFAULT_FRONTEND_SERVICE_GLOBS
        )
        frontend_routes = parse_frontend_routes(frontend_patterns)
        frontend_count = len(frontend_routes)
        frontend_only, frontend_matched = diff_frontend_routes(frontend_routes, rs_routes)

    if args.json:
        payload = {
            "python_route_count": len(py_routes),
            "rust_route_count": len(rs_routes),
            "only_in_python": [{"method": method, "path": path} for method, path in py_only],
            "only_in_rust": [{"method": method, "path": path} for method, path in rs_only],
        }
        if args.frontend:
            payload.update(
                {
                    "frontend_route_count": frontend_count,
                    "frontend_rust_path_count": len({path for _, path in rs_routes}),
                    "frontend_matched": frontend_matched,
                    "only_in_frontend": [
                        {"method": method, "path": path} for method, path in frontend_only
                    ],
                }
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            Report(
                py_count=len(py_routes),
                rs_count=len(rs_routes),
                only_in_py=py_only,
                only_in_rs=rs_only,
            ).as_markdown()
        )
        if args.frontend:
            print("")
            print(
                FrontendReport(
                    frontend_count=frontend_count,
                    rs_count=len({path for _, path in rs_routes}),
                    matched_count=frontend_matched,
                    only_in_frontend=frontend_only,
                ).as_markdown()
            )

    return int(bool(py_only or frontend_only))


if __name__ == "__main__":
    raise SystemExit(main())

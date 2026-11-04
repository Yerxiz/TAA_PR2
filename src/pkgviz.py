import argparse
import os
import re
import sys
from urllib.parse import urlparse
from apt_repo import (RepoError, fetch_repo_content, find_package,
                      parse_packages, load_test_graph)
import subprocess
import shutil

PROG = "pkgviz"
TOOL_VERSION = "0.1.0"

REPO_MODES = ("local", "remote", "test")
TREE_MODES = ("off", "on", "compact")
IMAGE_EXTENSIONS = (".png", ".svg", ".pdf", ".dot", ".jpg", ".jpeg")

PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,213}$")

VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")

BAD_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def validate_package(value: str) -> str:
    """Проверяет имя пакета."""
    if not value or not value.strip():
        raise argparse.ArgumentTypeError("package name must not be empty")
    if not PACKAGE_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid package name {value!r}: "
            "allowed characters are letters, digits, '.', '-', '_'"
        )
    return value


def validate_repo(value: str) -> str:
    """Проверяет, что значение --repo не пустое.
    Более сложная проверка (URL это или файл) зависит от --repo-mode
    и делается позже, в validate_cross().
    """
    if not value or not value.strip():
        raise argparse.ArgumentTypeError("repository must not be empty")
    return value


def validate_repo_mode(value: str) -> str:
    """Проверяет режим работы с репозиторием."""
    if value not in REPO_MODES:
        raise argparse.ArgumentTypeError(
            f"invalid repo mode {value!r}: "
            f"choose one of {', '.join(REPO_MODES)}"
        )
    return value


def validate_version(value: str) -> str:
    """Проверяет версию пакета. Специальное значение 'latest' допустимо."""
    value = value.strip()
    if value.lower() == "latest":
        return "latest"
    if not VERSION_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid version {value!r}: "
            "allowed characters are letters, digits, '.', '-', '_', '+'"
        )
    return value


def validate_output(value: str) -> str:
    """Проверяет имя выходного файла с изображением графа."""
    if not value:
        raise argparse.ArgumentTypeError("output filename must not be empty")
    if BAD_FILENAME_CHARS.search(value):
        raise argparse.ArgumentTypeError(
            f"invalid output filename {value!r}: "
            "contains forbidden characters (<>:\"/\\|?*)"
        )
    if os.path.basename(value) != value:
        raise argparse.ArgumentTypeError(
            "output filename must not contain directory separators"
        )
    ext = os.path.splitext(value)[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        raise argparse.ArgumentTypeError(
            f"output filename must end with one of: "
            f"{', '.join(IMAGE_EXTENSIONS)}"
        )
    return value


def validate_tree_mode(value: str) -> str:
    """Проверяет режим вывода ASCII-дерева."""
    if value not in TREE_MODES:
        raise argparse.ArgumentTypeError(
            f"invalid ASCII tree mode {value!r}: "
            f"choose one of {', '.join(TREE_MODES)}"
        )
    return value


def validate_filter(value: str) -> str:
    """Проверяет подстроку для фильтрации пакетов."""
    const_number = 256
    if not value:
        raise argparse.ArgumentTypeError("filter substring must not be empty")
    if len(value) > const_number:
        raise argparse.ArgumentTypeError(
            "filter substring is too long (max 256 characters)"
        )
    if any(ord(c) < 0x20 for c in value):
        raise argparse.ArgumentTypeError(
            "filter substring must not contain control characters"
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG, description="Visualize package dependency graphs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter    )
    parser.add_argument("-p", "--package", required=True,
                        type=validate_package,
                        help="Name of the package to analyze."
                        )
    parser.add_argument(
        "-r", "--repo", required=True, type=validate_repo,
        help="Repository URL or path to a test repository file."
    )
    parser.add_argument(
        "--repo-mode", default="local", type=validate_repo_mode,
        help=f"How to interpret --repo. One of: {', '.join(REPO_MODES)}."
    )
    parser.add_argument("--version", default="latest",
                        type=validate_version,
                        help="Package version, or 'latest' for the newest."
                        )
    parser.add_argument("-o", "--output", default="deps.png",
                        type=validate_output, help="Output image filename."
                        )
    parser.add_argument(
        "--ascii-tree", default="on", type=validate_tree_mode,
        help=f"ASCII tree output mode. One of: {', '.join(TREE_MODES)}."
    )
    parser.add_argument(
        "--filter", default=None, type=validate_filter,
        help="Substring to filter package names (optional)."
    )
    parser.add_argument(
        "--tool-version", action="version", version=f"{PROG} {TOOL_VERSION}",
        help="Show the tool's own version and exit."
    )
    parser.add_argument(
        "--load-order", action="store_true",
        help="Print the dependency load (installation) order."
    )
    return parser


def validate_cross(args: argparse.Namespace,
                   parser: argparse.ArgumentParser) -> None:
    """Проверки, зависящие от комбинации нескольких параметров."""
    mode = args.repo_mode
    repo = args.repo

    if mode == "remote":
        parsed = urlparse(repo)
        if parsed.scheme not in ("http", "https"):
            parser.error(
                f"--repo must be an http(s) URL when --repo-mode=remote, "
                f"got {repo!r}"
            )
        if not parsed.netloc:
            parser.error(
                f"--repo URL must contain a host part, got {repo!r}"
            )

    elif mode == "local":
        if not os.path.exists(repo):
            parser.error(
                f"--repo path does not exist when --repo-mode=local: {repo!r}"
            )
        if not os.path.isfile(repo):
            parser.error(
                f"--repo must point to a file when --repo-mode=local: "
                f"{repo!r}"
            )


def dump_config(args: argparse.Namespace) -> None:
    """Печатает все параметры в формате ключ-значение."""
    rows = [
        ("package", args.package),
        ("repo", args.repo),
        ("repo_mode", args.repo_mode),
        ("version", args.version),
        ("output", args.output),
        ("ascii_tree", args.ascii_tree),
        ("filter", args.filter if args.filter is not None else "<none>"),
    ]
    width = max(len(k) for k, _ in rows)
    print("=== Configuration ===")
    for key, value in rows:
        print(f"{key:<{width}} : {value}")
    print("=====================")


def print_dependencies(pkg) -> None:
    """Печатает прямые зависимости пакета в виде списка."""
    print(f"Dependencies of {pkg.name} {pkg.version}:")
    if not pkg.depends:
        print("  (no dependencies)")
        return
    for dep in pkg.depends:
        print(f"  - {dep}")


def bfs_recursive(
        queue: list[str],
        repo_map: dict[str, list[str]],
        graph: dict[str, set[str]],
        visited: set[str],
        filter_sub: str | None) -> None:
    """Рекурсивный поиск в ширину для построения транзитивного графа.
    queue — узлы текущего уровня.
    visited — уже обработанные узлы (защита от циклов).
    """
    if not queue:
        return

    next_queue: list[str] = []

    for node in queue:
        if node in visited:
            continue
        visited.add(node)

        if filter_sub and filter_sub in node:
            continue

        if node not in graph:
            graph[node] = set()

        for dep in repo_map.get(node, []):
            if filter_sub and filter_sub in dep:
                continue

            graph[node].add(dep)

            if dep not in visited:
                next_queue.append(dep)

    bfs_recursive(next_queue, repo_map, graph, visited, filter_sub)


def print_graph(graph: dict[str, set[str]], root: str) -> None:
    """Печатает граф зависимостей в формате adjacency list."""
    print(f"\nDependency graph for {root}:")
    for node in sorted(graph.keys()):
        deps = sorted(graph[node])
        if deps:
            print(f"  {node} -> {', '.join(deps)}")
        else:
            print(f"  {node} -> (no dependencies)")


def get_load_order(graph: dict[str, set[str]], root: str) -> list[str]:
    """Вычисляет порядок загрузки зависимостей (топологическая сортировка).
    Использует рекурсивный DFS (post-order). Циклы разрываются.
    """
    order: list[str] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def dfs(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            return

        visiting.add(node)

        for dep in sorted(graph.get(node, [])):
            dfs(dep)

        visiting.remove(node)
        visited.add(node)
        order.append(node)

    dfs(root)
    return order


def generate_dot(graph: dict[str, set[str]], title: str) -> str:
    """Генерирует текстовое представление графа на языке DOT."""
    lines = [
        "digraph Dependencies {",
        '    rankdir="LR";',
        f'    label="{title}";',
        '    labelloc="t";',
        '    node [shape=box, style="rounded,filled", fillcolor="#e8f0fe", '
        'fontname="Arial"];',
        '    edge [color="#5f6368"];'
    ]
    for node in sorted(graph.keys()):
        for dep in sorted(graph[node]):
            lines.append(f'    "{node}" -> "{dep}";')
    lines.append("}")
    return "\n".join(lines)


def save_graph_image(dot_code: str, output_file: str) -> None:
    """Сохраняет граф в изображение через системный Graphviz."""
    if not shutil.which("dot"):
        print("warning: 'dot' (Graphviz) not found in PATH. "
              "Image not generated.", file=sys.stderr)
        print("         Install Graphviz from https://graphviz.org/download/",
              file=sys.stderr)
        return

    ext = os.path.splitext(output_file)[1].lstrip(".").lower()
    if ext == "jpg": ext = "jpeg"

    try:
        subprocess.run(
            ["dot", f"-T{ext}", "-o", output_file],
            input=dot_code.encode("utf-8"),
            check=True,
            capture_output=True
        )
        print(f"Graph image saved to: {output_file}")
    except subprocess.CalledProcessError as exc:
        print(f"error: Graphviz failed to render image: "
              f"{exc.stderr.decode()}", file=sys.stderr)


def print_ascii_tree(graph: dict[str, set[str]], root: str) -> None:
    """Печатает граф в виде ASCII-дерева."""
    print(f"\nDependency Tree for {root}:")
    visited = set()

    def _walk(node: str, prefix: str, is_last: bool) -> None:
        connector = "└── " if is_last else "├── "

        if node in visited:
            print(f"{prefix}{connector}{node} (cycle)")
            return

        print(f"{prefix}{connector}{node}")
        visited.add(node)

        children = sorted(graph.get(node, []))
        for i, child in enumerate(children):
            is_last_child = (i == len(children) - 1)
            next_prefix = prefix + ("    " if is_last else "│   ")
            _walk(child, next_prefix, is_last_child)

    print(root)
    visited.add(root)
    children = sorted(graph.get(root, []))
    for i, child in enumerate(children):
        is_last = (i == len(children) - 1)
        _walk(child, "", is_last)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_cross(args, parser)
    dump_config(args)
    try:
        if args.repo_mode == "test":
            repo_map = load_test_graph(args.repo)
            if args.package not in repo_map:
                raise RepoError(f"package {args.package!r} "
                                f"not found in test graph")
        else:
            content = fetch_repo_content(args.repo, args.repo_mode)
            packages = parse_packages(content)
            root_pkg = find_package(packages, args.package, args.version)
            repo_map = {}
            for p in packages:
                if p.name not in repo_map:
                    repo_map[p.name] = p.depends
            repo_map[root_pkg.name] = root_pkg.depends
        graph: dict[str, set[str]] = {}
        visited: set[str] = set()
        bfs_recursive([args.package], repo_map, graph, visited, args.filter)
        print_graph(graph, args.package)
        dot_code = generate_dot(graph, f"Dependencies of {args.package}")
        with open("deps.dot", "w", encoding="utf-8") as f:
            f.write(dot_code)
        save_graph_image(dot_code, args.output)
        if args.ascii_tree != "off":
            print_ascii_tree(graph, args.package)
        if args.load_order:
            print(f"\nLoad order for {args.package}:")
            load_order = get_load_order(graph, args.package)
            for i, pkg in enumerate(load_order, 1):
                print(f"  {i:>2}. {pkg}")
    except RepoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

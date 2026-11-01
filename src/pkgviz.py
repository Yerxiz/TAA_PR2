#!/usr/bin/env python3
import argparse
import os
import re
import sys
from urllib.parse import urlparse

PROG = "pkgviz"
TOOL_VERSION = "0.1.0"

# ---- Допустимые значения параметров ----
REPO_MODES = ("local", "remote", "test")
TREE_MODES = ("off", "on", "compact")
IMAGE_EXTENSIONS = (".png", ".svg", ".pdf", ".dot", ".jpg", ".jpeg")

# ---- Регулярные выражения ----
# Имя пакета: начинается с буквы или цифры, далее допустимы . - _
PACKAGE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,213}$")

# Версия: буквы, цифры, . - _ +
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")

# Символы, недопустимые в именах файлов (Windows + POSIX)
BAD_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


# ============================================================
#  Валидаторы отдельных параметров (используются как type=)
# ============================================================

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
    if not value:
        raise argparse.ArgumentTypeError("filter substring must not be empty")
    if len(value) > 256:
        raise argparse.ArgumentTypeError(
            "filter substring is too long (max 256 characters)"
        )
    if any(ord(c) < 0x20 for c in value):
        raise argparse.ArgumentTypeError(
            "filter substring must not contain control characters"
        )
    return value


# ============================================================
#  Парсер и перекрёстная валидация
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Visualize package dependency graphs (stage 1 prototype).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-p", "--package",
        required=True,
        type=validate_package,
        help="Name of the package to analyze.",
    )
    parser.add_argument(
        "-r", "--repo",
        required=True,
        type=validate_repo,
        help="Repository URL or path to a test repository file.",
    )
    parser.add_argument(
        "--repo-mode",
        default="local",
        type=validate_repo_mode,
        help=f"How to interpret --repo. One of: {', '.join(REPO_MODES)}.",
    )
    parser.add_argument(
        "--version",
        default="latest",
        type=validate_version,
        help="Package version, or 'latest' for the newest.",
    )
    parser.add_argument(
        "-o", "--output",
        default="deps.png",
        type=validate_output,
        help="Output image filename.",
    )
    parser.add_argument(
        "--ascii-tree",
        default="on",
        type=validate_tree_mode,
        help=f"ASCII tree output mode. One of: {', '.join(TREE_MODES)}.",
    )
    parser.add_argument(
        "--filter",
        default=None,
        type=validate_filter,
        help="Substring to filter package names (optional).",
    )
    parser.add_argument(
        "--tool-version",
        action="version",
        version=f"{PROG} {TOOL_VERSION}",
        help="Show the tool's own version and exit.",
    )
    return parser


def validate_cross(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
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
                f"--repo must point to a file when --repo-mode=local: {repo!r}"
            )

    # mode == "test": --repo игнорируется, любые значения допустимы


# ============================================================
#  Вывод конфигурации
# ============================================================

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


# ============================================================
#  Точка входа
# ============================================================

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate_cross(args, parser)
    dump_config(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

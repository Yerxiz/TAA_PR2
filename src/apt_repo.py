import gzip
import re
import urllib.error
import urllib.request
from dataclasses import dataclass


class RepoError(Exception):
    """Ошибка получения или разбора данных репозитория."""


@dataclass
class Package:
    name: str
    version: str
    depends: list[str]  # прямые зависимости (только имена)
    fields: dict[str, str]  # все поля записи (для будущих этапов)


# ============================================================
#  Загрузка содержимого репозитория
# ============================================================

def fetch_repo_content(repo: str, mode: str) -> str:
    """Возвращает текст файла Packages.

    mode="local"  — repo это путь к файлу.
    mode="remote" — repo это http(s) URL.
    mode="test"   — берёт встроенный тестовый файл.
    """
    if mode == "test":
        return _TEST_PACKAGES
    if mode == "local":
        return _read_local(repo)
    if mode == "remote":
        return _read_remote(repo)
    raise RepoError(f"unknown repo mode: {mode!r}")


def _read_local(path: str) -> str:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        raise RepoError(f"cannot read repository file {path!r}: {exc}") from exc
    return _decode(raw, path)


def _read_remote(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = resp.read()
    except urllib.error.URLError as exc:
        raise RepoError(f"cannot fetch {url!r}: {exc}") from exc
    return _decode(raw, url)


def _decode(raw: bytes, source: str) -> str:
    """Определяет gzip по магическим байтам, иначе — utf-8."""
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(raw)
        except OSError as exc:
            raise RepoError(f"failed to decompress {source!r}: {exc}") from exc
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RepoError(f"repository {source!r} is not valid UTF-8: {exc}") from exc


# ============================================================
#  Разбор поля Depends
# ============================================================

def parse_depends(value: str) -> list[str]:
    """Из строки 'a (>= 1.0), b, c | d' извлекает ['a', 'b', 'c']."""
    result = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        # отбрасываем альтернативы через '|', берём первую
        first_alt = part.split("|")[0].strip()
        # отбрасываем ограничение версии: 'name (>= 1.0)' -> 'name'
        name = re.split(r"\s+", first_alt, maxsplit=1)[0]
        name = name.rstrip(":")  # редкий случай 'name:any'
        if name:
            result.append(name)
    return result


# ============================================================
#  Разбор файла Packages на записи
# ============================================================

def parse_packages(text: str) -> list[Package]:
    """Возвращает список всех пакетов из текста Packages."""
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    last_key: str | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip():
            # пустая строка = конец текущей записи
            if current:
                records.append(current)
                current = {}
                last_key = None
            continue

        if raw_line[0] in (" ", "\t") and last_key:
            # продолжение многострочного поля — нам не критично, но соберём
            current[last_key] += "\n" + raw_line.strip()
            continue

        if ":" not in raw_line:
            continue  # мусорная строка — пропускаем

        key, _, val = raw_line.partition(":")
        key = key.strip()
        current[key] = val.strip()
        last_key = key

    if current:
        records.append(current)

    packages: list[Package] = []
    for rec in records:
        name = rec.get("Package")
        version = rec.get("Version")
        if not name or not version:
            continue  # без имени/версии запись бесполезна
        depends = parse_depends(rec.get("Depends", ""))
        packages.append(Package(name=name, version=version,
                                depends=depends, fields=rec))
    return packages


# ============================================================
#  Поиск нужного пакета
# ============================================================

def find_package(packages: list[Package], name: str,
                 version: str) -> Package:
    """Ищет пакет по имени и версии.

    Если version == 'latest', возвращает первое найденное совпадение
    по имени (в реальных файлах Packages обычно идёт от новых к старым).
    """
    matches = [p for p in packages if p.name == name]
    if not matches:
        raise RepoError(f"package {name!r} not found in repository")
    if version == "latest":
        return matches[0]
    for p in matches:
        if p.version == version:
            return p
    available = ", ".join(p.version for p in matches[:5])
    raise RepoError(
        f"version {version!r} of {name!r} not found. "
        f"Available versions: {available}"
    )


# ============================================================
#  Встроенный тестовый репозиторий (для --repo-mode=test)
# ============================================================

_TEST_PACKAGES = """\
Package: myapp
Version: 1.0.0
Architecture: amd64
Depends: libc6 (>= 2.31), libssl1.1, zlib1g
Description: My demo app v1

Package: myapp
Version: 2.0.0
Architecture: amd64
Depends: libc6 (>= 2.34), libssl3, libcurl4 | libcurl3, libzstd1
Description: My demo app v2

Package: libc6
Version: 2.35-0ubuntu3
Architecture: amd64
Depends: libgcc-s1
Description: GNU C Library

Package: libssl1.1
Version: 1.1.1f-1ubuntu2
Architecture: amd64
Depends: libc6 (>= 2.25)
Description: SSL library (old)

Package: libssl3
Version: 3.0.2-0ubuntu1.12
Architecture: amd64
Depends: libc6 (>= 2.34)
Description: SSL library

Package: zlib1g
Version: 1:1.2.11.dfsg-2ubuntu9
Architecture: amd64
Depends: libc6 (>= 2.14)
Description: Compression library
"""

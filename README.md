# pkgviz

Инструмент визуализации графа зависимостей пакетов. Этап 1:
минимальный CLI-прототип с настраиваемыми параметрами.

## Содержание

1. [Общее описание](#1-общее-описание)
2. [Параметры командной строки](#2-параметры-командной-строки)
3. [Запуск](#3-запуск)
4. [Примеры использования](#4-примеры-использования)

---

## 1. Общее описание

`pkgviz` — CLI-инструмент, который по имени пакета строит и
визуализирует граф его зависимостей. На этапе 1 реализованы только
разбор и валидация параметров и вывод конфигурации; реальное
построение графа добавляется на следующих этапах.

## 2. Параметры командной строки

| Параметр | Обязательный | По умолчанию | Описание |
|---|---|---|---|
| `-p`, `--package <name>` | да | — | Имя анализируемого пакета |
| `-r`, `--repo <url-or-path>` | да | — | URL репозитория или путь к файлу тестового репозитория |
| `--repo-mode <mode>` | нет | `local` | Режим работы: `local`, `remote`, `test` |
| `--version <ver>` | нет | `latest` | Версия пакета или `latest` |
| `-o`, `--output <file>` | нет | `deps.png` | Имя файла с изображением графа |
| `--ascii-tree <mode>` | нет | `on` | Режим ASCII-дерева: `off`, `on`, `compact` |
| `--filter <substring>` | нет | — | Подстрока для фильтрации имён пакетов |
| `--tool-version` | — | — | Показать версию инструмента и выйти |

## 3. Запуск

Требуется Python 3.10+. Внешних зависимостей нет.

```bash
python src/pkgviz.py --package requests --repo ./fixtures/sample-repo.json
```

## 4. Примеры использования

### Базовая конфигурация (local mode)

```bash
python src/pkgviz.py \
    --package requests \
    --repo ./fixtures/sample-repo.json
```

```
=== Configuration ===
package    : requests
repo       : ./fixtures/sample-repo.json
repo_mode  : local
version    : latest
output     : deps.png
ascii_tree : on
filter     : <none>
=====================
```

### Все параметры заданы

```bash
python src/pkgviz.py \
    --package numpy \
    --repo https://pypi.org/simple \
    --repo-mode remote \
    --version 1.26.0 \
    --output numpy-deps.svg \
    --ascii-tree compact \
    --filter "lib"
```

```
=== Configuration ===
package    : numpy
repo       : https://pypi.org/simple
repo_mode  : remote
version    : 1.26.0
output     : numpy-deps.svg
ascii_tree : compact
filter     : lib
=====================
```

### Обработка ошибок

Каждый параметр валидируется отдельно. Ошибки выводятся в stderr,
код возврата — 2.

| Что передано | Сообщение |
|---|---|
| `--package ""` | `package name must not be empty` |
| `--package "bad name!"` | `invalid package name 'bad name!': allowed characters are letters, digits, '.', '-', '_'` |
| `--repo ""` | `repository must not be empty` |
| `--repo-mode banana` | `invalid repo mode 'banana': choose one of local, remote, test` |
| `--repo-mode local --repo /nowhere` | `--repo path does not exist when --repo-mode=local: '/nowhere'` |
| `--repo-mode remote --repo ./file.txt` | `--repo must be an http(s) URL when --repo-mode=remote, got './file.txt'` |
| `--version "!!!"` | `invalid version '!!!': allowed characters are letters, digits, '.', '-', '_', '+'` |
| `--output ""` | `output filename must not be empty` |
| `--output "../deps.png"` | `output filename must not contain directory separators` |
| `--output deps.txt` | `output filename must end with one of: .png, .svg, .pdf, .dot, .jpg, .jpeg` |
| `--ascii-tree maybe` | `invalid ASCII tree mode 'maybe': choose one of off, on, compact` |
| `--filter ""` | `filter substring must not be empty` |
| (без `--package`) | `the following arguments are required: -p/--package` |
| (без `--repo`) | `the following arguments are required: -r/--repo` |
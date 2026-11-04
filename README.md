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

| Параметр                     | Обязательный | По умолчанию | Описание                                               |
|------------------------------|--------------|--------------|--------------------------------------------------------|
| `-p`, `--package <name>`     | да           | —            | Имя анализируемого пакета                              |
| `-r`, `--repo <url-or-path>` | да           | —            | URL репозитория или путь к файлу тестового репозитория |
| `--repo-mode <mode>`         | нет          | `local`      | Режим работы: `local`, `remote`, `test`                |
| `--version <ver>`            | нет          | `latest`     | Версия пакета или `latest`                             |
| `-o`, `--output <file>`      | нет          | `deps.png`   | Имя файла с изображением графа                         |
| `--ascii-tree <mode>`        | нет          | `on`         | Режим ASCII-дерева: `off`, `on`, `compact`             |
| `--filter <substring>`       | нет          | —            | Подстрока для фильтрации имён пакетов                  |
| `--tool-version`             | —            | —            | Показать версию инструмента и выйти                    |

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

| Что передано                           | Сообщение                                                                                 |
|----------------------------------------|-------------------------------------------------------------------------------------------|
| `--package ""`                         | `package name must not be empty`                                                          |
| `--package "bad name!"`                | `invalid package name 'bad name!': allowed characters are letters, digits, '.', '-', '_'` |
| `--repo ""`                            | `repository must not be empty`                                                            |
| `--repo-mode banana`                   | `invalid repo mode 'banana': choose one of local, remote, test`                           |
| `--repo-mode local --repo /nowhere`    | `--repo path does not exist when --repo-mode=local: '/nowhere'`                           |
| `--repo-mode remote --repo ./file.txt` | `--repo must be an http(s) URL when --repo-mode=remote, got './file.txt'`                 |
| `--version "!!!"`                      | `invalid version '!!!': allowed characters are letters, digits, '.', '-', '_', '+'`       |
| `--output ""`                          | `output filename must not be empty`                                                       |
| `--output "../deps.png"`               | `output filename must not contain directory separators`                                   |
| `--output deps.txt`                    | `output filename must end with one of: .png, .svg, .pdf, .dot, .jpg, .jpeg`               |
| `--ascii-tree maybe`                   | `invalid ASCII tree mode 'maybe': choose one of off, on, compact`                         |
| `--filter ""`                          | `filter substring must not be empty`                                                      |
| (без `--package`)                      | `the following arguments are required: -p/--package`                                      |
| (без `--repo`)                         | `the following arguments are required: -r/--repo`                                         |

## Этап 2. Сбор данных

Инструмент умеет загружать файл `Packages` из репозитория Ubuntu
и извлекать прямые зависимости для указанной версии пакета.

### Источники данных

| `--repo-mode` | Что делает `--repo`                                    |
|---------------|--------------------------------------------------------|
| `local`       | путь к файлу `Packages` на диске                       |
| `remote`      | http(s) URL файла `Packages` или `Packages.gz`         |
| `test`        | встроенный тестовый репозиторий, `--repo` игнорируется |

### Формат, который поддерживается

Формат `Packages` (Debian / Ubuntu). Из каждой записи используются
поля `Package`, `Version`, `Depends`. Поле `Depends` разбирается
до списка имён (без версий и без альтернатив):

```
Depends: libc6 (>= 2.34), libssl3, libcurl4 | libcurl3
→ ['libc6', 'libssl3', 'libcurl4']
```

### Примеры использования

**Локальный файл (этап 2 demo):**

```bash
python src/pkgviz.py \
    --package myapp \
    --repo ./fixtures/Packages \
    --repo-mode local \
    --version 2.0.0
```

Ожидаемый вывод (после раздела Configuration):

```
Dependencies of myapp 2.0.0:
  - libc6
  - libssl3
  - libcurl4
  - libzstd1
```

**С `--version latest`:**

```bash
python src/pkgviz.py \
    --package myapp --repo ./fixtures/Packages --version latest
```

```
Dependencies of myapp 1.0.0:
  - libc6
  - libssl1.1
  - zlib1g
```

(`latest` возвращает первое совпадение — на реальных зеркалах
записи идут от новых к старым, поэтому первая запись и есть `latest`.)

**Встроенный тестовый репозиторий (без сети и без файлов):**

```bash
python src/pkgviz.py \
    --package myapp --repo unused --repo-mode test --version 2.0.0
```

**Реальный репозиторий Ubuntu:**

```bash
python src/pkgviz.py \
    --package bash \
    --repo http://archive.ubuntu.com/ubuntu/dists/jammy/main/binary-amd64/Packages.gz \
    --repo-mode remote
```

(Файл большой, скачивание займёт несколько секунд. Это
**единственный** вариант, где нужен интернет; всё остальное
работает офлайн.)

### Обработка ошибок этапа 2

| Ситуация                      | Сообщение                                                     | Код возврата |
|-------------------------------|---------------------------------------------------------------|--------------|
| Файл `Packages` не существует | `cannot read repository file '...': ...`                      | 1            |
| Сетевая ошибка                | `cannot fetch '...': ...`                                     | 1            |
| Битый gzip                    | `failed to decompress '...': ...`                             | 1            |
| Кодировка не UTF-8            | `repository '...' is not valid UTF-8: ...`                    | 1            |
| Пакет не найден               | `package 'foo' not found in repository`                       | 1            |
| Версия не найдена             | `version '1.2.3' of 'foo' not found. Available versions: ...` | 1            |

## Этап 3. Основные операции

Инструмент строит транзитивный граф зависимостей, корректно обрабатывает
циклы и поддерживает фильтрацию.

### Сборка графа

Для обхода графа используется **рекурсивный поиск в ширину (BFS)**.
Это гарантирует, что даже при наличии циклов (A → B → C → A) программа
не уйдёт в бесконечную рекурсию — посещённые узлы запоминаются в `visited`.

### Фильтрация

Параметр `--filter <substring>` исключает из графа любые пакеты
(и их ветви зависимостей), имена которых содержат указанную подстроку.
Сравнение чувствительно к регистру.

### Тестовый режим

При `--repo-mode test` параметр `--repo` должен указывать на **JSON-файл**
с описанием графа. Имена пакетов — большие латинские буквы.

Формат файла:

```json
{
  "A": [
    "B",
    "C"
  ],
  "B": [
    "D"
  ],
  "C": [
    "D",
    "E"
  ]
}
```

Пример запуска (с фильтрацией):

```bash
python src/pkgviz.py \
    --package A \
    --repo fixtures/test_graph.json \
    --repo-mode test \
    --filter C
```
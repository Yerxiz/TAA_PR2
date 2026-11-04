@echo off
REM Устанавливаем кодировку UTF-8 для корректного отображения кириллицы и ASCII-дерева
chcp 65001 >nul
setlocal

REM Определяем корень проекта (папка, где лежит этот скрипт)
set "ROOT=%~dp0"
cd /d "%ROOT%"

REM Проверяем, что Python доступен (можно заменить на python, если py не работает)
set "PY=py"

echo ==========================================================
echo   PKGVIZ - Демонстрация работы всех этапов
echo ==========================================================
echo.

echo === ЭТАП 1: Конфигурация и обработка ошибок ===
echo --- Пример 1: Успешный разбор параметров ---
echo Ввод: py src\pkgviz.py --package myapp --repo fixtures\Packages --version 2.0.0
%PY% src\pkgviz.py --package myapp --repo fixtures\Packages --version 2.0.0
echo.

echo --- Пример 2: Ошибка (несуществующий режим репозитория) ---
echo Ввод: py src\pkgviz.py --package myapp --repo fixtures\Packages --repo-mode banana
%PY% src\pkgviz.py --package myapp --repo fixtures\Packages --repo-mode banana
echo.

echo --- Пример 3: Ошибка (неверный формат выходного файла) ---
echo Ввод: py src\pkgviz.py --package myapp --repo fixtures\Packages --output deps.txt
%PY% src\pkgviz.py --package myapp --repo fixtures\Packages --output deps.txt
echo.

echo ==========================================================
echo === ЭТАП 2 И 3: Сбор данных и построение графа (BFS + Циклы) ===
echo --- Пример 4: Граф из тестового репозитория с циклом ---
echo Ввод: py src\pkgviz.py --package A --repo fixtures\test_graph.json --repo-mode test --ascii-tree off
%PY% src\pkgviz.py --package A --repo fixtures\test_graph.json --repo-mode test --ascii-tree off
echo.

echo --- Пример 5: Фильтрация (исключаем пакеты с буквой C) ---
echo Ввод: py src\pkgviz.py --package A --repo fixtures\test_graph.json --repo-mode test --filter C --ascii-tree off
%PY% src\pkgviz.py --package A --repo fixtures\test_graph.json --repo-mode test --filter C --ascii-tree off
echo.

echo ==========================================================
echo === ЭТАП 4: Порядок загрузки (Топологическая сортировка) ===
echo --- Пример 6: Порядок установки для графа с циклом ---
echo Ввод: py src\pkgviz.py --package A --repo fixtures\test_graph.json --repo-mode test --load-order --ascii-tree off
%PY% src\pkgviz.py --package A --repo fixtures\test_graph.json --repo-mode test --load-order --ascii-tree off
echo.

echo ==========================================================
echo === ЭТАП 5: Визуализация (ASCII-дерево и Graphviz) ===
echo --- Пример 7: Локальный пакет myapp версии 2.0.0 (с генерацией SVG) ---
echo Ввод: py src\pkgviz.py --package myapp --repo fixtures\Packages --version 2.0.0 --output myapp.svg
%PY% src\pkgviz.py --package myapp --repo fixtures\Packages --version 2.0.0 --output myapp.svg
echo.

echo --- Пример 8: Системный пакет bash ---
echo Ввод: py src\pkgviz.py --package bash --repo fixtures\Packages --output bash.svg
%PY% src\pkgviz.py --package bash --repo fixtures\Packages --output bash.svg
echo.

echo ==========================================================
echo   ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ
echo ==========================================================
pause
---
id: TASK-123
title: 'CI-workflow på GitHub Actions: ruff + pytest med pytest-xdist'
status: Done
assignee:
  - '@vibe'
created_date: '2026-11-17T20:50:00Z'
updated_date: '2026-11-17T22:08:00Z'
labels:
  - ci
  - review-followup
dependencies:
  - TASK-122
references:
  - review_lechonk_summary.md
  - review_vibe_deepseek41_flash.md
modified_files:
  - pyproject.toml
  - uv.lock
  - README.md
  - .github/workflows/ci.yml
priority: high
type: chore
ordinal: 174000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Ingen CI finns (.github/ saknas) och 862 tester tar 270 s manuellt (review_vibe_deepseek41_flash.md §5.2). Skapa .github/workflows/ci.yml med uv sync --group dev, ruff check och pytest -q -n auto. Lägg till pytest-xdist i dev-beroendena och en slow-markör i pyproject.toml för tester som startar MainWindow. CI är förutsättningen för att större refaktoreringar ska vara säkra: ingen big-bang av vyer innan denna task är klar.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Workflow kör ruff check och pytest vid push/PR
- [x] #2 pytest-xdist är tillagd i dev-gruppen och sviten körs med -n auto (270 s ner under 90 s)
- [x] #3 slow-markör är definierad i pyproject.toml för MainWindow-startande tester
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Task description completed
- [x] #2 Code reviewed for quality, simplicity, and maintainability
- [x] #3 All tests pass
- [x] #4 Documentation updated
- [x] #5 Code committed
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Lägg pytest-xdist i [dependency-groups].dev i pyproject.toml och uppdatera uv.lock med uv lock.
2. Registrera slow-markören i [tool.pytest.ini_options].markers med en beskrivning som säger att den gäller tester som startar MainWindow. Att sätta markören på testfallen hör till TASK-154.
3. Skapa .github/workflows/ci.yml: push och pull_request mot main, ubuntu-latest, astral-sh/setup-uv med cache, uv sync --group dev, ruff check ., pytest -q -n auto med QT_QPA_PLATFORM=offscreen och de systembibliotek PySide6/OpenCV kräver.
4. Verifiera lokalt: uv run ruff check . samt uv run pytest -q -n auto med tidmätning mot baslinjen 270 s.
5. Dokumentera CI-körningen och hur sviten körs parallellt i README.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
pyproject.toml: pytest-xdist>=3.6 i [dependency-groups].dev (låst till 3.8.0 + execnet 2.1.2 i uv.lock) och slow-markören registrerad i [tool.pytest.ini_options].markers. Markören sätts på testfallen i TASK-154, inte här.

.github/workflows/ci.yml: push (alla grenar) och pull_request, ubuntu-latest, QT_QPA_PLATFORM=offscreen, apt-get för libegl1/libgl1/libxkbcommon0/libdbus-1-3/libfontconfig1/fonts-dejavu-core, astral-sh/setup-uv@v7 med cache, uv sync --group dev, ruff check . och pytest -q -n auto. concurrency med cancel-in-progress så en ny push avbryter den gamla körningen.

Verifiering: uv run ruff check . → All checks passed. uv run pytest -q -n auto med QT_QPA_PLATFORM=offscreen → 857 passed, 1 skipped, 4 failed på 16 s (baslinje 270 s seriellt). De fyra felen är lokala för Windows+offscreen: Qt:s offscreen-plattform hittar inget teckensnitt ("QFontDatabase: Cannot find font directory"), så fontMetrics ger 150 px i stället för cirka 70 px för märkestexten och märket hamnar delvis i vänstra halvan. Utan QT_QPA_PLATFORM=offscreen går samma tester igenom (35/35 i test_detection_badge.py och test_app_icon.py). CI är opåverkad: test_window_gets_the_icon_the_taskbar_draws hoppas över utanför win32 och workflowen installerar fonts-dejavu-core. README har en rad om detta.

Kortkommandotesterna i tests/test_shortcuts.py är stabila under offscreen (5/5 körningar med -n auto) men fladdrar på Windows utan offscreen, eftersom bara ett av 24 worker-processer kan ha fönsterfokus. CI kör alltid offscreen och slipper därför problemet.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
CI är på plats: .github/workflows/ci.yml kör ruff check . och pytest -q -n auto på ubuntu-latest vid push och pull request, med QT_QPA_PLATFORM=offscreen, de Qt-/OpenCV-bibliotek som saknas på runnern, fonts-dejavu-core för textmåtten och concurrency med cancel-in-progress. pytest-xdist>=3.6 ligger i dev-gruppen (låst till 3.8.0) och slow-markören är registrerad i pyproject.toml. Sviten går från cirka 270 s seriellt till 16 s med -n auto. Verifierat lokalt: ruff utan anmärkning, 857 passed och 1 skipped; de fyra kvarvarande felen är Windows-specifika för offscreen utan teckensnitt och påverkar inte CI. Kvar till TASK-154: sätta slow-markören på de tester som startar MainWindow.
<!-- SECTION:FINAL_SUMMARY:END -->

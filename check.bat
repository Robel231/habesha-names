@echo off
call .venv\Scripts\activate.bat
pytest -q && ruff check . && mypy src --strict

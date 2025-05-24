# MCP Python SDK Agent Guide

## Commands
- Format: `uv run --frozen ruff format .`
- Lint: `uv run --frozen ruff check .`
- Fix lint: `uv run --frozen ruff check . --fix`
- Type check: `uv run --frozen pyright`
- Test all: `uv run --frozen pytest`
- Test single: `uv run --frozen pytest tests/path/to/test.py::test_name`
- If pytest plugin issues: `PYTEST_DISABLE_PLUGIN_AUTOLOAD="" uv run --frozen pytest`

## Code Style
- Package manager: ONLY use uv, NEVER pip
- Line length: 88 chars maximum
- Type hints required for all code
- Public APIs need docstrings
- Async testing: use anyio, not asyncio
- Break long strings with parentheses
- Explicit None checks for Optional types
- Follow existing code patterns exactly
- Import sorting: use Ruff (I001)
- Keep functions small and focused
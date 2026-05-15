# Contributing

Thanks for considering a contribution. This project is for Lutron integrators and homeowners; PRs that make the app more accurate, more useful, or easier to install are very welcome.

## Ground rules

- Be kind. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).
- The README's "Planned (M2+)" section is the rough roadmap. Issues/PRs touching M2+ scope are great, but expect them to be staged behind M1 stability first.
- Don't commit real Lutron processor serials, MAC addresses, or PEM files. The `.gitignore` blocks the obvious paths; the `scripts/sanitize-snapshot.py` helper scrubs the rest. The `examples/sanitized-snapshot.json` fixture is the only inventory blob in the repo.

## Dev setup

See the [README's Development section](README.md#development).

## Coding standards

### Python
- Python 3.10+. Use `list[str]` / `dict[str, X]` / `X | None`, not `List`/`Optional`.
- Async throughout the backend. No `requests` in async paths — use `httpx`.
- `ruff check` + `ruff format` clean. Line length 100.
- Type hints on public functions. Pydantic v2 models for everything that crosses an API or storage boundary.
- Don't write multi-line docstrings on internal helpers; well-named identifiers and short module-level docstrings are enough.

### TypeScript / React
- TypeScript `strict: true`. No `any` without an inline reason comment.
- React 18 function components only. Hooks for state.
- Tailwind for styling. shadcn/ui primitives only — no other component libraries.
- ESLint + Prettier clean.
- All user-facing strings go through the i18n catalog (`frontend/src/i18n/`). No hardcoded English in components.

### Models
- Lutron-mirror models (anything that parses raw LEAP) keep PascalCase field names and use `extra="allow"` so new firmware fields don't break parsing.
- App-internal DTOs use snake_case and `extra="forbid"`.

## Tests

- Backend: `pytest` against the recorded fixtures + mock LEAP server. CI blocks merges on failures.
- Frontend: `vitest` for component tests.
- New extraction logic must come with a fixture-based test; reach into a real processor only in manual end-to-end runs.

## Pull requests

1. Open an issue first for anything non-trivial (>~50 LOC). It's easier to align on approach early than to rewrite on review.
2. Branch off `main`. Keep PRs focused — one feature or fix per PR.
3. Update `CHANGELOG.md` under `[Unreleased]`.
4. CI must be green.
5. We squash-merge.

## Reporting bugs

Use the issue templates. For LEAP-related bugs, please include:
- Processor model and firmware version (visible in the app's About panel or `/server/1/status/ping`).
- The relevant slice of `lutron_raw.json` (sanitized via `scripts/sanitize-snapshot.py`).
- Steps to reproduce.

## Security

Don't open public issues for security problems. Email the maintainer listed in `pyproject.toml`.

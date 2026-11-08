# Maintenance instructions for Codex

## Privacy boundary

- Never commit real conversations, corpora, personal profiles, review candidates,
  decisions, or private sensitive-word lists. Keep generated data in ignored
  `corpus/` or outside the checkout; personal profiles belong in `~/.style-polish/`.
- Use synthetic data for tests, issues, PR examples and screenshots. Do not open,
  quote or print real user messages during maintenance. When a user authorizes a
  local validation, let scripts process source stores read-only and report counts
  and success/failure only. Do not change or delete session stores.
- Before every commit or PR, inspect the staged file list for private artifacts,
  run all tests and the leak gate. Never bypass a failed gate:

  ```sh
  python3 -m unittest discover -s tests -v
  python3 scripts/check.py --leak-gate examples/spoken.example.md
  ```

  Integration tests also run the gate on generated synthetic profiles and verify
  that it rejects synthetic private data. For a locally generated personal profile,
  run the gate locally with its matching entity list; do not upload either file:

  ```sh
  python3 scripts/check.py --leak-gate ~/.style-polish/spoken.md --sensitive corpus/auto_sensitive.json
  ```

## Adapters and regression tests

- Read `scripts/collect.py` and trace the pipeline in `scripts/run.py` first.
  Follow an existing adapter (for example `Pi`): implement default paths and
  `parse(path)`, emit the same metadata, register it in `ADAPTERS`, and keep source
  files read-only (SQLite uses `ro_sqlite`). Reuse existing cleanup/filtering.
- Add synthetic fixtures and tests for the real supported format, user/assistant
  separation, injected/tool messages, empty stores and relevant malformed records.
  Use temporary HOME and working directories; tests must never discover real HOME.
- Reproduce bugs with failing regression tests before the smallest fix. A pipeline
  success requires usable samples, a generated profile and a passing leak gate.

## Releases and documentation

- Keep `README.md` (English) and `README.zh-CN.md` in sync whenever installation,
  commands, behavior or release claims change. Update `docs/compatibility.md` for
  adapter support and limitations; do not claim untested formats work.
- Python 3.9+ and the standard library are the baseline. Run the full suite on 3.9
  and a current Python; CI covers both. No package installation is required.
- Before delivery, run `git diff --check` and review `git diff --cached --name-only`.
  Keep generated local artifacts out of commits even when a leak gate passes.

# CLAUDE.md

Guidance for Claude (or any AI assistant) working on this repo.

## What this is

Flask + Jinja2 web app that generates hardened SCTE-35 plugin scaffolds for the Uplynk LiveSlicer. Users fill out a web form, get back a zip containing a plugin, reference conf, README, and CHANGELOG.

Deployed at `plugin.telcomjj.com` (LAN-only). Push to `main` → GitHub Action → Pi redeploys in ~90s.

## Before editing

- **Always read the current session handoff** if the user provided one — it captures per-session state (what shipped, what's parked, current `GENERATOR_VERSION`).
- **Read `CHANGELOG.md`** for shipped-version context if no handoff is available.
- **Read the target template before editing it.** Jinja templates in `templates/plugin/` interact via a shared context — don't guess at variable names.

## Bump policy

Update `GENERATOR_VERSION` at the top of `app.py` with every commit that changes behavior:

- **PATCH** (`0.5.0` → `0.5.1`) — cosmetic fixes, small bugfixes, deploy infra
- **MINOR** (`0.5.0` → `0.6.0`) — new template shipped, new preset, new feature
- **MAJOR** — reserved for `1.0.0`

Every generated file carries `{{ generator_version }}` in its footer so users can trace what built their plugin.

## Repo conventions

- **File placement:** templates live in `templates/plugin/`. Repo-root files (`README.md`, `CHANGELOG.md`, `CLAUDE.md`) are static, not templated.
- **Naming:** `_method_<preset>.py.j2` for method files, `_<helper>.py.j2` for shared helpers. Leading underscore signals "included, not standalone."
- **Jinja env:** the plugin templates use `StrictUndefined` + `trim_blocks=True` + `lstrip_blocks=True`. Undefined variables raise; whitespace after block tags is stripped. Watch for `trim_blocks` eating newlines you meant to keep — use filter expressions (`{{ x | filter }}`) instead of `{% for %}` loops when you need a trailing newline preserved.
- **Code fences in Markdown templates:** use standard triple-backtick fences. If nesting is a concern, use `~~~` at your own risk — some renderers don't handle them.

## Workflow discipline

- **One preset/feature = one PR-sized change.** Don't bundle unrelated edits.
- **Chunk large template writes.** For anything over ~100 lines, deliver in sections and pause for the user to test between chunks.
- **When updating `app.py`'s `generate()` route to emit a new file, always do both the render AND the writestr in the same commit.** Shipping a template without wiring it up produces a silent regression.
- **Pi git config gotcha:** if a deploy fails with `fatal: Cannot rebase onto multiple branches`, the Pi needs `git config pull.rebase false && git config pull.ff only` in the repo. Already applied on the current Pi; document it if a new Pi is ever provisioned.

## Parked work

- **OON preset** — scaffolding kept dormant in `scte_plugin.py.j2` (all gated by `{% if has_oon %}`, which is hardcoded `False`). Revival steps documented in the S3 handoff. Do not remove the dormant scaffolding without user confirmation.

## Never do

- Never rename or delete a template file without explicit user confirmation — the file rename cheat sheet in S3 handoff exists because of a prior rename that confused things for a session.
- Never commit `GENERATOR_VERSION` bumps without a corresponding CHANGELOG.md entry at the repo root.
- Never edit files under `/mnt/user-data/uploads` or other read-only mounts — those are user artifacts, not the working repo.

## When in doubt

Ask. The user (Jeff) prefers a clarifying question over a wrong assumption, especially about SCTE-35 semantics or Uplynk-specific slicer behavior.

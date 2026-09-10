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
- **Macros need explicit context passing.** When a template `{% import %}`s another for its macros, the imported macros DO NOT see the caller's context by default. Use `{% import '_method_linear_common.py.j2' as common with context %}`. Symptom of forgetting: `UndefinedError: 'm' is undefined` inside the macro even though `m` is defined in the caller.
- **Family-of-presets pattern.** For presets that share most of a method body (see `_method_linear_common.py.j2`), extract shared code into a Jinja macro with a `{{ caller() | indent(N, first=True) }}` variance point. Child templates use `{% call common.macro_name(m.name) %}...{% endcall %}` to provide the preset-specific block. `indent(N, first=True)` is not optional — the child template's block starts at col 0 in source and needs to land at the macro's indent depth in output. This is how `_method_linear.py.j2` and `_method_linear_type5_segids.py.j2` share ~600 lines of Type 6 handling while each provides its own Type 5 dispatch.
- **Code fences in Markdown templates:** use standard triple-backtick fences. If nesting is a concern, use `~~~` at your own risk — some renderers don't handle them.

## Workflow discipline

- **One preset/feature = one PR-sized change.** Don't bundle unrelated edits.
- **Chunk large template writes.** For anything over ~100 lines, deliver in sections and pause for the user to test between chunks.
- **When updating `app.py`'s `generate()` route to emit a new file, always do both the render AND the writestr in the same commit.** Shipping a template without wiring it up produces a silent regression.
- **Verify rendered plugins parse.** After any template change, render at least one plugin end-to-end and run `python3 -c "import ast; ast.parse(open('scte_<name>.py').read()); print('OK')"`. Catches indent bugs, missing/extra parens, unclosed blocks — the class of error that only shows up when the LiveSlicer tries to load the file. Two v1.4.x releases shipped syntactically broken plugins because this check wasn't in the workflow. 20ms per render — cheaper than any bug it catches.
- **AST-equivalence check on refactors.** When restructuring a template that should preserve output (extracting macros, deduping, reorganizing), render both old and new versions with the same context, parse both with `ast.parse()`, dump both with `ast.dump(tree, indent=2)`, and diff the dumps. AST-identical output is stronger proof than byte-identical because it ignores comment/whitespace shuffling that doesn't affect what Python actually executes. Used in v1.5.0's chunk 1 refactor to prove the common-macro extraction preserved every Linear code path exactly.
- **Pi git config gotcha:** if a deploy fails with `fatal: Cannot rebase onto multiple branches`, the Pi needs `git config pull.rebase false && git config pull.ff only` in the repo. Already applied on the current Pi; document it if a new Pi is ever provisioned.

## Release gotchas

Things that bit past sessions, kept here so they don't bite the next one:

- **Tags vs releases.** `git push origin v1.0.1` pushes a tag. GitHub's release badge (shields.io) only sees *releases*, not tags. Create the release with `gh release create <tag> --title "..." --notes-from-tag` or via the web UI at `/releases`.
- **Camo image cache.** `camo.githubusercontent.com` caches badge/image URLs. If a badge stays stale after the underlying data has changed, either wait (usually clears in a few minutes) or bust it by appending a nonsense query param like `&v=2` to the badge URL and committing.
- **Emoji variation selectors in header anchors.** Emojis with variation selectors (🎛️ = U+1F39B U+FE0F, 🏗️ = U+1F3D7 U+FE0F) produce anchor slugs that include the selector — e.g. `## 🎛️ Available features` becomes `#️-available-features`, not `#-available-features`. Copy the slug GitHub actually generates rather than guessing.
- **`git add <file>` only stages files with unstaged modifications.** If a file was edited then reverted between the edit and the `git add`, or if a prior `git commit` already picked up the change, `git add` is a no-op and produces no warning. Watch commit output for unexpectedly low `N file(s) changed` counts.
- **Development happens on two machines.** The Mac at `~/github/scte-plugin-generator/` is the dev workstation where edits happen. The Pi at `~/git/scte-plugin-generator/` is the deploy target where GitHub Actions runs `git pull`. When giving shell commands, ask (or state) which machine — differences that matter: BSD sed on Mac needs `sed -i '' "..."`, GNU sed on Pi wants `sed -i "..."` (no empty string). BSD sed and GNU sed also diverge on `-E` vs `-r` for extended regex, and on `-n` addressing (BSD `sed -n 'l'` shows line-end markers; GNU `sed -n 'l'` truncates at 70 cols by default). `cat -A` for whitespace inspection is GNU-only — BSD `cat` errors on `-A`; use `sed -n 'l'` or `od -c` instead. Paths differ (`~/github/` vs `~/git/`). Force-pushes on Mac break the Pi's next `git pull --ff-only` since the Pi's local history no longer matches origin — recover with `ssh` to Pi, `git fetch origin && git reset --hard origin/main`, then retrigger deploy with an empty commit.
- **File delivery via chat cards can silently fail.** When handing large files to the user, `present_files`-style cards sometimes show "No file content available" despite the file existing on disk. There's no error surfaced — the user just sees an empty card. If the user reports an empty file, fall back to pasting content inline in fenced code blocks. Cost is a longer message; benefit is guaranteed delivery. Prefer inline paste for anything the user needs to save verbatim (templates, config files).

## Parked work

- **OON preset** — scaffolding kept dormant in `scte_plugin.py.j2` (all gated by `{% if has_oon %}`, which is hardcoded `False`). Revival steps documented in the S3 handoff. Do not remove the dormant scaffolding without user confirmation.

## Never do

- Never rename or delete a template file without explicit user confirmation — the file rename cheat sheet in S3 handoff exists because of a prior rename that confused things for a session.
- Never commit `GENERATOR_VERSION` bumps without a corresponding CHANGELOG.md entry at the repo root.
- Never edit files under `/mnt/user-data/uploads` or other read-only mounts — those are user artifacts, not the working repo.
- Never create empty template files as placeholders "reserved for future use." Only create a template file when there's actual content to put in it. Empty scaffolding gets included in every generated plugin as dead code and creates confusion the next time someone looks at the file wondering why it exists. Adding a template later is a two-minute change; removing accumulated placeholder cruft is a whole-session chore.

## When in doubt

Ask. The user prefers a clarifying question over a wrong assumption, especially about SCTE-35 semantics or Uplynk-specific slicer behavior.
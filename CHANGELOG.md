# Changelog

All notable changes to `scte-plugin-generator` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Version bump policy:
- **PATCH** — cosmetic fixes, small bugfixes, deploy infra changes
- **MINOR** — new template shipped, new preset, new feature, meaningful capability change
- **MAJOR** — reserved for `1.0.0` (complete G-series + full app zip expansion)

## [Unreleased]

### Added
-

### Changed
-

### Fixed
-

## [0.5.0] - 2026-08-21

### Added
- `CHANGELOG.md.j2` template — Keep a Changelog format with seeded initial release entry (Turn G3).
- Repo `README.md` and `CHANGELOG.md`.
- `generate()` route now emits `<plugin_name>/CHANGELOG.md` in the zip.

## [0.4.3] - 2026-08-21

### Fixed
- Code block rendering in generated README:
  - Unindented bash blocks in Installation section (were nested under numbered list items with 3-space indent, causing leading whitespace inside rendered code blocks).
  - Added explicit `text` language hint to architecture ASCII tree fence.

## [0.4.1] - 2026-08-21

### Fixed
- Wired `README.md` render into `generate()` route (0.4.0 shipped the template but forgot the app.py plumbing).

## [0.4.0] - 2026-08-21

### Added
- `README.md.j2` template — comprehensive generated README with end-user and developer sections plus SCTE-35 refresher (Turn G2).
- Full emoji treatment on the README template: section headers, preset/feature callouts, troubleshooting entries, table cells.

## [0.3.3] - 2026-08-21

### Fixed
- Blank line after `channel_group:` line in generated conf. Switched channel_group selection from `{% for %}` loop to filter expression so `trim_blocks` doesn't eat the trailing newline.

## [0.3.1] - 2026-08-21

### Fixed
- Tightened whitespace around `channel_group:` header in generated conf.

## [0.3.0] - 2026-08-21

### Added
- `example.conf.j2` template — full reference `uplynk.conf` with sections gated by Jinja context (Turn G1).
- Selected presets/features emit active keys; unselected are emitted commented for reference.
- Secrets rendered as `<CHANGEME_*>` placeholders; structural values from Disney sample.
- `generate()` route now emits `<plugin_name>/uplynk.conf` in the zip.

## [0.2.0] - 2026-08-20

### Added
- `_method_scte_logger.py.j2` — SCTELogger channel_group method as a selectable preset. Data-driven descriptor loop over `_SCTE_LOGGER_TABLE`, full SCTE-35 seg coverage (0x00–0x51), hex+decimal in log lines, graceful UPID decode with binary hex fallback, unknown seg_id fallback.
- SCTELogger tile in form.
- `has_scte_logger` derived boolean in `build_context()`.

### Changed
- `Process35` dispatcher fully loop-driven (removed hardcoded `if channel_group == 'scte_logger':` branch).
- Restored "at least one method required" validation in `build_context()` (was commented out while SCTELogger was the safety net; now re-enabled since a zero-method plugin is truly empty).

### Removed
- OON tile from form. Preset scaffolding kept dormant in `scte_plugin.py.j2` for future revival.

### Fixed
- File rename: OLD `_method_scte_logger.py.j2` (which was actually seg-type helpers) → `_log_helpers.py.j2`. New file with the same old name now holds the actual SCTELogger method. See handoff docs for the confusing history.

## [0.1.0] - 2026-08-20

### Added
- `_method_live_event.py.j2` — Disney live event lifecycle preset. Types 0/16/17/19/20/54/55, command_type 5 branch. Inline `_type16_callback` / `_terminal_update_cb` / `_start_event_cb` closures over per-event state (Turn E).

## [0.0.2] - 2026-08-20

### Changed
- Live-event Chunk A test bump.

## [0.0.1] - 2026-08-19

### Added
- Initial scaffold: Flask app, form, deploy pipeline (Turn S1).
- Uplynk-style dark theme with magenta (#ec1e79) accent.
- GitOps deploy: push to `main` → GitHub Action SSHes to Pi → `docker compose up -d --build`.
- LAN-only exposure via Pi-hole CNAME + Caddy on Utility Pi.
- `_method_linear.py.j2` with all 12 CNBC diff corrections applied.
- `scte_plugin.py.j2` master template with sections 1-5 + entrypoints + method-loop includes.
- Baseline hardening patterns: leak-safe scte_message summary dict, float exec-time comparison, `_parse_bool_config()`, uppercase log levels, redacted apikey copy for log output.
- `/healthz` liveness endpoint.

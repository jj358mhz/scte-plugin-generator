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

## [1.3.0] — 2026-09-03

### Fixed
- **Linear preset, Type 5 (splice_insert) dispatch rewritten to OON-first.** The previous dispatch branched on `'duration' in command` and `duration != 0` before OON, which silently misrouted three cases:
  - **OON=1 with `duration_flag=0`** (open-ended affiliate pod start, e.g. CBS-style) fell into the zero-duration skip branch. `AdStart` never fired. Any correct ad-break behavior on affected channels was coming from outside the plugin (slicer's own SCTE processing, upstream ad server, or base64 metadata routing).
  - **OON=0 with `duration_flag=0`** (return-to-network with no duration) hit the same skip path. `AdEnd` never fired.
  - **OON=0 with a duration present** hit the `oon == 1` branch's `else` and logged "in-network, no action, skipping." `AdEnd` never fired.

  New dispatch:
  - `oon == 1` + `duration_flag == 0` → one-arg `slicer.AdStart(pts)` (open-ended; mating OON=0 closes)
  - `oon == 1` + `duration_flag == 1` → two-arg `slicer.AdStart(pts, duration)` (unchanged behavior for the previously-working path)
  - `oon == 0` → `slicer.AdEnd(pts)`
  - unexpected/missing OON → warning log, no action

### Changed
- **Type 5 open-ended `AdStart` uses one-arg form** per Uplynk slicer API (`slicer.AdStart(int(pts))`, `Duration` omitted). Documented at https://docs.uplynk.com/docs/scte-plugin-slicer-module#adstart.
- **Type 5 `out_of_network_indicator` no longer defaults to 0** on missing field. Messages arriving without the OON field now log a warning and take no action, rather than silently firing `AdEnd`.
- **Type 5 with `duration_flag=1` but `duration=0`** now refuses to call `AdStart(pts, 0)` and logs an error. Calling `AdStart` with duration=0 disables the slicer's auto-return timer and can trap the slicer in-break if the mating OON=0 is lost — same defensive posture already applied to Type 6 zero-duration STARTs in `_handle_time_signal_ad_breaks`.
- **`boundary_handling` + open-ended OON=1** (duration_flag=0) now logs a warning and skips. Boundary mode emits a synchronous StartBoundary/EndBoundary pair and requires a known duration; open-ended breaks cannot be bounded. Boundary and ad-break calls do not mix within a channel — under `use_boundary=True`, everything routes to `StartBoundary`/`EndBoundary`; under `use_boundary=False`, everything routes to `AdStart`/`AdEnd`.

### Migration notes
Any customer running `linear` + `splice_insert` who was seeing missed `AdStart`/`AdEnd` events will now see them fire correctly. **If you built a workaround to compensate for the silent misrouting** (upstream ad-server calls, slicer-side SCTE handling, base64 metadata routing that duplicates what the plugin now does), remove it before regenerating — otherwise you may see double-firing on affected breaks.

## [1.2.1] — 2026-09-03

### Fixed
- **`Notify()` signature now accepts `pts` argument.** Per the Uplynk slicer contract, `Notify(pts)` is invoked with a PTS argument whenever a `SetNotify()` callback is registered. The previous zero-arg signature would `TypeError` and crash the slicer process on invocation. Latent bug — no current customer config wires up SetNotify — but a real crash for anyone who does.
- **Type 6 zero-duration START events now correctly skip both AdStart and the matching AdEnd.** Previously the `ZERO_DUR` bool was set True and immediately reset to False on the same line, so the END-side guard was dead code. If a provider sent a segmentation descriptor with `segmentation_duration=0`, the plugin would still call `AdStart(pts, 0)` — which disables the slicer's auto-return timer and, combined with a missing mating END, sends the slicer into an infinite ad break. This scenario bit an affiliate several years ago and drove the original (broken) fix. The correct implementation records the offending `(start_id, end_id)` pair in a `ZERO_DUR_PAIRS` set on START, consults and clears it on END, and evicts stale entries on any subsequent valid START for the same pair.

### Changed
- **Removed duplicated `dur_off_x` / `pts_off_x` calls in the Type 6 START handler.** Offsets are now computed once, after the duration check, only when needed.

## [1.2.0] — 2026-09-03

### Added
- **Linear preset: SCTE-35 segmentation type 50/51 (Distributor Advertisement) as an opt-in pair.** New form checkbox alongside 32/33, 34/35, 48/49, 54/55. Unchecked by default — existing default pair selection unchanged.
- **Linear preset: per-seg-id timing offset keys in `uplynk.conf`.** The reference config now emits `pts_offset_<start>`, `pts_offset_<end>`, and `duration_offset_<start>` for every selected pair, plus `pts_offset_16` for Program Start and `pts_offset_500` / `pts_offset_501` / `duration_offset_501` for splice_insert OON timing. Previously these keys were consumed by the plugin at runtime but not surfaced in the reference config; users had to know to add them. Existing deployments are unaffected — the keys default to 0 whether present or not.

### Changed
- **Linear preset: `ad_break_ids_seen` observation list now includes 50/51.** When `scte_ad_break_mode='splice_insert'` and a Type 6 message arrives carrying Distributor Advertisement seg IDs, the "observed but ignoring" log line now reports them instead of silently dropping them.

### Docs
- **Generated plugin README: SCTE-35 refresher table adds rows for 0x32/0x33 (Distributor Advertisement Start/End).** The Provider vs Distributor paragraph below the table now distinguishes "advertisement" pairs (0x30/0x31, 0x32/0x33) from "placement opportunity" pairs (0x34/0x35, 0x36/0x37).

## [1.1.2] - 2026-08-22

### Added
- Documented Mac-vs-Pi dev/deploy split in `CLAUDE.md` release gotchas
  section. Captures BSD vs GNU sed syntax differences, path layout
  differences, and force-push recovery procedure on the Pi.

## [1.1.1] - 2026-08-22

### Added
- 🔌 favicon on the generator UI (`plugin.telcomjj.com`). Inline SVG data
  URI in `form.html` `<head>` — no assets, no build step, emoji renders
  as the browser tab icon across all modern browsers.

## [1.1.0] - 2026-08-21

### Fixed
- `example.conf.j2`: added `plugin_memory_logging: false` — was read by
  `Process35()` on every invocation but never surfaced in the generated conf.
- `example.conf.j2`: added `allow_scte_wakeup: false` as a commented-out
  user-tunable key (gates whether Type 16 can pull the slicer out of
  blackout). Previously buried in the wrong comment block.
- `example.conf.j2`: `boundary_handling` feature block now emits all four
  sub-keys (`boundary_name_local`, `boundary_name_national`,
  `boundary_name_oon`, `boundary_duration_max`) — all were missing.
- `scte_plugin.py.j2`: `boundary_mode()` was reading `use_boundary` from
  config but the conf key was always `boundary_handling`. Parser and conf
  now agree.
- `example.conf.j2`: linear preset block now emits `outofnetwork_mode`,
  `local_mode`, `passthrough_mode`, `program_start_via_scte_mode`,
  `scte_ad_break_mode`, `ad_skip_spliceinsert`, `ad_skip_timesignal` — all
  were read by linear parsers but absent from the generated conf.
- `example.conf.j2`: removed duplicate `local_mode`, `passthrough_mode`,
  `outofnetwork_mode` from the live event block (conflict with linear block;
  live event block's `local_mode: 0` was also semantically wrong — the key
  is a tri-state string, not a boolean).
- `example.conf.j2`: runtime-injected keys (`profile`, `signal_type`)
  correctly labeled as non-user-configurable in a separate comment block.

## [1.0.3] - 2026-08-22

### Changed
- Alphabetized imports in `scte_plugin.py.j2` with PEP 8 stdlib/third-party
  grouping. `# stdlib` and `# third-party` comment headers, blank line
  between groups, alpha within each group. Conditional imports keep their
  Jinja gates but sort into their alpha position. isort- and ruff-friendly.

## [1.0.2] - 2026-08-22

### Added
- New "Release gotchas" section in `CLAUDE.md`: tag-vs-release distinction,
  Camo image cache behavior, emoji variation selectors in header anchors,
  `git add` no-op on clean files. Captures workflow gotchas from S4 that
  would otherwise recur.
- New "Never do" rule in `CLAUDE.md` against creating placeholder template
  files "reserved for future use." Closes the loop on the
  `_log_helpers.py.j2` mistake.

## [1.0.1] - 2026-08-22

### Added
- Release badge in repo `README.md` — auto-tracks latest `v*` GitHub
  release via shields.io. Uses Uplynk magenta (`#ec1e79`).

### Fixed
- Broken TOC anchors in repo `README.md` — the 🎛️ and 🏗️ emojis contain
  variation selectors (U+FE0F) that GitHub's slugifier preserves in the
  anchor. TOC entries had been pointing at selector-stripped slugs and
  404'ing.
- Restored `[1.0.0]` CHANGELOG entry that was accidentally clobbered
  between tagging `v1.0.0` and pushing the release-badge commit.

## [1.0.0] - 2026-08-22

First feature-complete release. Complete G-series template set, full app zip
expansion, repo-level docs, post-ship housekeeping, and release badge all landed.

### Added
- Release badge in repo `README.md` — auto-tracks latest `v*` tag.
- Repo-level `CLAUDE.md` guidance for AI assistants (see `0.5.1` entry).

### Changed
- Bumped to `1.0.0` — G-series complete, zip expansion complete, cleanup pass
  complete. Bump policy met the MAJOR criterion.

### Fixed
- Broken TOC anchors in repo `README.md` — the 🎛️ and 🏗️ emojis contain
  variation selectors (U+FE0F) that GitHub's slugifier preserves in the
  anchor. TOC entries had been pointing at selector-stripped slugs and
  404'ing.

### Removed
- **`_log_helpers.py.j2`** template. The file was a rename artifact from S3 —
  intended as a home for helpers used by `log()`, but never grew helpers worth
  extracting. Its actual contents (an old SCTELogger implementation and
  duplicate `_SCTE_SEG_TYPES` seg-type table) were dead code because
  `_method_scte_logger.py.j2` redefines `SCTELogger` later in the include
  order. Removed the file and its include line from `scte_plugin.py.j2`. If
  `log()` ever grows helpers worth extracting, the file can be recreated in
  a two-minute change.
- **Vestigial live_event async helpers** from `scte_plugin.py.j2` Section 4:
  `_type16_callback`, `_terminal_update_cb`, `_start_event_cb`,
  `_TYPE16_PTS_CACHE`. Never called — `_method_live_event.py.j2` supersedes
  them with inline closures that capture per-event state (`external_id`,
  `pts`, `pts_offset`, `id3_mode`, `call_sign`, etc.) directly, which the
  module-level versions couldn't do cleanly.

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

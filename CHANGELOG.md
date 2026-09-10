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

## [1.5.0] - 2026-09-09

### Added
- New preset: `linear_type5_segids`. Generates a `LinearType5SegIds` method for operators whose encoder emits `segmentation_descriptor` pairs inside `splice_insert` (Type 5) commands rather than the conventional `time_signal` (Type 6) carriage. Uncommon but SCTE-35-conformant; customer-driven addition. Type 6 dispatch identical to Standard Linear; Type 5 dispatch selected at runtime by `outofnetwork_mode` in `uplynk.conf`. When `outofnetwork_mode=1`, Type 5 dispatches via the OON path (identical to Standard Linear semantics). When `outofnetwork_mode=0`, Type 5 dispatches via `_handle_time_signal_ad_breaks` against the Type 5 command's descriptors, using `segmentation_duration` and `pts_offset_<seg_id>`, honoring `ad_break_scope`. The two presets share every runtime config key — one `uplynk.conf` serves whichever method the slicer's `channel_group` dispatches to.
- New template file: `_method_linear_common.py.j2`. Two Jinja macros extracted from what was 609 lines of duplicated Linear-family method body. `linear_method(method_name)` renders the `def <name>(...)` body with `command_type == 5` as a `{% call %}` variance point; `linear_helpers()` renders the module-level `_handle_time_signal_ad_breaks` helper. `_method_linear.py.j2` and `_method_linear_type5_segids.py.j2` are thin child templates that provide their preset-specific Type 5 dispatch inline. `_handle_time_signal_ad_breaks` is descriptor-container-agnostic — it operates on `seg_type_list` and `descriptors` regardless of whether they came from Type 5 or Type 6, enabling zero-code reuse across the two presets.
- New form UX: LinearType5SegIds method card in `form.html`, positioned between Standard Linear and Live Event. All form field names suffixed `_linear_type5_segids` (matching the preset-suffix convention established in v1.4.0) for clean multi-instance expansion in v1.6.0+.
- `outofnetwork_mode` config key now gates Type 5 dispatch in **both** Linear-family presets. Was metadata-only before v1.5.0 (parsed, logged, passed as `MetaMetadata`, but not consulted for dispatch). In Standard Linear, `outofnetwork_mode=0` now log-and-skips all Type 5 messages; `outofnetwork_mode=1` restores prior behavior. In LinearType5SegIds, `outofnetwork_mode=0` selects the descriptor-driven path; `outofnetwork_mode=1` selects the OON path.

### Changed
- `example.conf.j2`: Linear preset config section renamed to "Linear / LinearType5SegIds preset config" and gated on `has_linear or has_linear_type5_segids`. Both presets emit into the same conf block since they share every runtime knob. Pair offset emission (`pts_offset_<start>`, `pts_offset_<end>`, `duration_offset_<start>`) deduplicates across both presets using a Jinja `_seen_pairs` accumulator — if both presets select the same seg-ID pair, its offsets emit once, not twice.
- `example.conf.j2`: added multi-line comment block above `outofnetwork_mode: 0` documenting its now-active preset-dependent semantics.
- `README.md.j2`: Standard Linear section adds a 🚦 callout describing `outofnetwork_mode`'s new dispatch-gate role. New `linear_type5_segids` section describes the two dispatch paths in a table (OON path vs. seg-ID path), lists baked-in pairs, notes the `outofnetwork_mode: 0` default choice, and warns operators about selecting both Linear-family presets in one plugin (config-key semantic differs across the two).
- `snake_to_pascal()` in `app.py`: no code change, but `LinearType5Segids` (rather than `LinearType5SegIds`) is the default method name for the new preset. Operators wanting `SegIds` casing use the "method name override" form field — same escape hatch that already exists for acronyms (CBS, NBC).

### Fixed
- Rendered plugin: `global ZERO_DUR_PAIRS` inside `_handle_time_signal_ad_breaks` was indented 8 spaces where the function body is at 4, producing `IndentationError: unexpected indent` on any generated plugin that reached that line at runtime. Introduced in v1.4.0 and invisible in that release because the v1.4.0 paren bug fixed in v1.4.1 short-circuited parsing before reaching this line. Detected during v1.5.0's chunk-1 refactor via `ast.parse()` on rendered output.

### Notes
- **Back-compat break for Standard Linear**: `outofnetwork_mode` was metadata-only in v1.4.x; v1.5.0 makes it a real gate. Generated plugins whose `uplynk.conf` has `outofnetwork_mode: 0` (the generator default) will now log-and-skip all Type 5 messages. Deployed customers upgrading Standard Linear from v1.4.x to v1.5.0 must set `outofnetwork_mode: 1` in `uplynk.conf` before restarting the slicer. Not a footgun in the maintainer's workflow (one slicer, one conf, one operator, QA before launch) but every operator regenerating in v1.5.0 needs to know.
- Two Linear-family presets share runtime config surface intentionally. `channel_group` in `uplynk.conf` picks which method actually dispatches at runtime; the shared config keys just mean the same conf file serves either method. Multi-linear support (allowing multiple named Linear methods with per-method configs — LinearCBS, LinearNBC, etc.) moves from v1.5.0 backlog to v1.6.0+.
- v1.4.2 backlog: remove dead `local_mode` code (helper defined but never called; config key silently no-op).
- v1.4.3 backlog: gate unselected preset sections out of generated `uplynk.conf`.
- Verification checklist for future releases: `ast.parse()` on rendered plugin output in every feature/preset combination. Catches the class of bug behind v1.4.1 hotfix and this release's `global` indent fix in ~20ms per render.

## [1.4.1] - 2026-09-09

### Fixed
- Rendered plugin: stray `)` after the `_handle_time_signal_ad_breaks(...)` call in the `command_type == 6` branch of `_method_linear.py.j2` caused `SyntaxError: unmatched ')'` on any plugin generated without the `boundary_handling` feature enabled. Plugins failed to load into the LiveSlicer runtime. Introduced in v1.4.0 during the `ad_break_scope` kwarg addition; every v1.4.0-generated plugin without boundary handling was affected. One-character delete; no behavior change to correctly-loading plugins.

### Notes
- Verification checklist for future releases now includes `ast.parse()` on rendered plugin output — catches this class of syntax bug in ~20ms per render.

## [1.4.0] - 2026-09-09

### Added
- `ad_break_scope` — new runtime config axis for Type 6 ad-break signaling. Splits ad-break segmentation type IDs into Provider role (48/49 Advertisement, 52/53 Placement Opportunity, 56/57 Overlay Placement Opportunity) vs. Distributor role (50/51 Advertisement, 54/55 Placement Opportunity, 58/59 Overlay Placement Opportunity), per SCTE 35. Three values: `provider`, `distributor`, `both` (default). Exposed as a radio group in the generator form; baked into `example.conf.j2` as the operator's default; enforced at runtime in `_handle_time_signal_ad_breaks` with an `[upl-py_Mode] ad_break_scope=<x>, observed but ignoring out-of-scope Type 6 seg_ids: [...]` log line for pairs baked in at gen time but scope-filtered at fire time.
- Three new Type 6 seg-ID pairs surfaced in the generator: 52/53 (Provider Placement Opportunity), 56/57 (Provider Overlay Placement Opportunity), 58/59 (Distributor Overlay Placement Opportunity). Form checkboxes ship unchecked by default.
- Rendered plugin: `PROVIDER_AD_SEG_IDS`, `DISTRIBUTOR_AD_SEG_IDS`, `ROLE_TAGGED_AD_SEG_IDS`, `ALL_AD_BREAK_SEG_IDS` frozenset constants replacing hardcoded seg-ID tuples in the mode-mismatch and scope-filter log lines. Adding a new pair to a role now touches one constant instead of every log site that lists ad-break IDs.
- Rendered plugin: `ad_break_scope()` config parser in `scte_plugin.py.j2`, `AD_BREAK_SCOPE = {}` memoization cache, and `_log_param('Ad break scope', ad_scope)` startup log in the Linear method.

### Changed
- Generator form field names normalized to preset-suffix convention: `seg_pair_XX_XX` → `seg_pair_XX_XX_linear`. Enables clean multi-instance expansion later (v1.5.0 multi-linear backlog) without a field-name migration inside the follow-up PR.
- Linear preset form UX restructured: pair checkboxes grouped into three semantic sections (outside role split / Provider role / Distributor role) with sub-headers, and a new "Runtime role scope" radio group above them.
- Rendered plugin: mode-mismatch "observed but ignoring" log now references `ALL_AD_BREAK_SEG_IDS` instead of the hardcoded 10-ID tuple — automatically picks up the three new pairs from this release.

### Notes
- Back-compat preserved: defaults (34/35 + 48/49 + 54/55, scope=both) reproduce pre-1.4 behavior byte-for-byte. Operators upgrading generated plugins do not need to change `uplynk.conf` — absent `ad_break_scope` defaults to `both` at runtime.
- `ad_break_scope` composes with `scte_ad_break_mode`: the filter only applies when `scte_ad_break_mode=time_signal`. Under `splice_insert` mode the scope value is read and logged but does nothing (Type 5 has no seg IDs to filter).
- Chapter (32/33) and Break (34/35) sit outside the role split and are unaffected by scope — if baked into the plugin at generation time, they fire regardless of `ad_break_scope`.
- v1.4.1 backlog: remove dead `local_mode` code from `scte_plugin.py.j2`, `_method_live_event.py.j2`, `example.conf.j2` (helper defined but never called; config key silently no-op).
- v1.4.2 backlog: gate unselected preset sections out of generated `uplynk.conf` (currently emitted commented-out even when preset code isn't compiled in, misleading operators about capability).

## [1.3.6] - 2026-09-08

### Added
- `from __future__ import annotations` at the top of `scte_plugin.py.j2`, immediately after the module docstring. Rendered plugins now defer evaluation of type annotations at runtime.

### Fixed
- Plugins rendered from v1.3.4 and v1.3.5 failed to load under LiveSlicer runtime with `AttributeError: module 'slicer' has no attribute 'SliceInfo'`. The `slicer.SliceInfo` (and other TypedDict) annotations introduced in v1.3.4 exist only in `uplynk-slicer-stubs` v0.2.0+ for static analysis; the runtime `slicer` C-extension module has no such attribute. Deferring annotation evaluation via `from __future__ import annotations` makes annotations lazy strings at runtime while preserving full type-checker visibility. No behavioral change to SCTE-35 handling in rendered plugins.

## [1.3.5] - 2026-09-05

### Fixed
- Rendered plugin (linear preset): `oon = command.get('out_of_network_indicator')` in `_method_linear.py.j2` was missing a default. When a `splice_insert` arrives without the field, `oon` becomes `None` and the downstream `if oon == 1:` / `if oon == 0:` branches both silently fall through, skipping OON handling entirely. Added explicit `, 0` default, matching the already-correct pattern in `_method_scte_logger.py.j2`. Latent bug fix — no runtime regression, but the missing-field case now dispatches correctly.

### Notes
- Discovered during post-v1.3.4 verification of the freshly-rendered WMA plugin.
- Rendered plugins now consistent across templates on OON extraction pattern.

## [1.3.4] - 2026-09-05

### Fixed
- Rendered plugin: eliminated the surviving `Any | None` cascade from `slice_info.get(...)` extractions that v1.3.3's parser annotations couldn't reach. Root cause was the untyped slicer runtime bridge — fixed jointly with `uplynk-slicer-stubs` v0.2.0, which introduces `SliceInfo`, `SpliceCommand`, and `SegmentationDescriptor` TypedDicts. Templates now annotate every function that receives `slice_info` (`Process35`, `break_dur`, `break_dur_oon`, and both channel-group methods `LinearNewsMax` / `SCTELogger`) with `slicer.SliceInfo`, so type flow propagates through the dispatch chain.
- Rendered plugin: `HandleCall` unused-parameter warnings. v1.3.3's `# noinspection PyUnusedLocal` above the def didn't apply because PyCharm scopes that inspection to local variables, not parameters. Renamed to `_origin_url`, `_response`, `_code`, `_request_id` — the standard "intentionally unused" convention for parameters. Safe because the slicer runtime calls `HandleCall` positionally.
- Rendered plugin: `_handle_time_signal_ad_breaks` unused-parameter warning on `slicer_id`. Genuinely unused in the function body (dead inherited param); renamed to `_slicer_id`. Sole caller in `_method_linear.py.j2` invokes positionally.
- Rendered plugin: workaround for a PyCharm inference bug on `total=False` TypedDict `.get()` lookups, where `descriptor.get('segmentation_type_id')` was wrongly inferred as `int` instead of `int | None`, marking the `if seg_id is None:` guard branch as unreachable. Added `# noinspection PyUnreachableCode` above the guard in `_method_scte_logger.py.j2`. The guard is genuinely reachable at runtime — malformed segmentation descriptors do occur.
- Rendered plugin: `slicer_id` inference at extraction. `slicer_values.get('slicerID')` returned `Any | None` because `slicer.GetStatus()` is currently typed as plain `dict` in the stubs. Added explicit `''` default to collapse the type at the extraction site until the stubs narrow `GetStatus()` in a future release.

### Notes
- Requires `uplynk-slicer-stubs >= 0.2.0` installed in the plugin's dev venv for PyCharm to resolve the new TypedDict annotations. Runtime plugins are unaffected — stubs are dev-only, not shipped with the plugin.
- Result: fresh WMA render (linear preset, default features) went from **24 PyCharm warnings under v1.3.3 to 0 under v1.3.4**.
- All template-side fixes are additive; no runtime behavior changes.

## [1.3.3] - 2026-09-04

### Fixed
- Rendered plugin: PyCharm frame-guard warning in `log()`. Replaced the compound `if frame is not None and frame.f_back is not None` guard with a nested guard that assigns `frame.f_back` to a local before dereferencing, so type narrowing sticks.
- Rendered plugin: type-narrowing cascade in `SlicerLogger()` f-strings. Added `-> str` / `-> int` / `-> bool` / `-> float` / `-> dict` return annotations to every config parser (`call_sign_id`, `gain_value`, `get_api_port`, `pts_off_x`, `dur_off_x`, `pt_mode`, `profile_id`, `scte_wakeup_enabled`, `signal_type`, `slicer_ver`, `stream_type_id`, `boundary_mode`, `boundary_duration_max`, `boundary_name_for`, `oon_mode`, `pgm_start_mode`, `local_mode`, `ad_break_mode`, `ad_skip_spliceinsert`, `ad_skip_timesignal`, `api_url`, `ad_meta_keys`, `meta_key`, `uac_mode`) and to `adis()`. Eliminates the `Any | None` inference that was fanning out into ~19 warnings across every generated plugin.
- Rendered plugin: unused-parameter warnings on `gain_value(gain=None)` (added `del gain`) and `HandleCall(origin_url, response, code, request_id)` (added `# noinspection PyUnusedLocal` above the def, since Jinja-branch analysis makes `del` unsafe when `has_live_event` / `has_oon` are enabled).

### Notes
- All fixes are template-side and additive — no runtime behavior changes.
- Rendered plugin version stamp still defaults to `0.0.1`; only `GENERATOR_VERSION` bumps.

## [1.3.2] - 2026-09-03

### Fixed
- Removed a stray `{% endif %}` in `templates/plugin/_method_linear.py.j2` that caused `TemplateSyntaxError: Encountered unknown tag 'endif'` when generating any linear-preset plugin. Introduced during the v1.3.0 Type 5 OON-first dispatch rewrite; latent because smoke-testing after v1.3.0 exercised the `live_event` and `oon` presets, not `linear`.

### Notes
- Generator-only fix. No changes to rendered plugin behavior, no `uplynk.conf` impact, no action needed for existing deployments. Users who tried to generate a linear preset between v1.3.0 and v1.3.2 would have seen the render error; regenerating after this release resolves it.

## [1.3.1] - 2026-09-03

### Fixed
- `get_slicer_metrics()` now caches its result for 5 seconds, preventing per-log-call blocking on the slicer's local `/status` endpoint. At `scte_log_verbosity: 3`, `log()` is invoked on every SCTE-35 message; the previous uncached 1-second HTTP timeout could push handler execution past `_EXEC_TIME_BUDGET` (250ms) on busy feeds — worst case when the slicer's own API was slow under load, which is precisely when metrics matter most.

### Changed
- `get_slicer_metrics()` HTTP timeout reduced from 1.0s to 0.5s. The TTL cache dampens fetch frequency enough that a tighter timeout further limits worst-case blocking on the rare cache-miss + slow-API combination.

### Notes
- Fully internal fix. No `uplynk.conf` changes required for existing deployments.
- Metrics values shown in verbosity=3 logs may now be up to 5 seconds stale. This is diagnostic output; acceptable trade for eliminating handler-thread blocking.

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

"""
Render-and-inspect tests for the generated SCTE plugin.

Every test renders scte_plugin.py.j2 the same way the /generate route does
(build_context -> plugin_env), then checks the output with `ast` or by
executing it against a stubbed `slicer` module. No LiveSlicer required.
"""
from __future__ import annotations

import ast
import collections
import itertools
import shutil
import subprocess
import sys
import types
from pathlib import Path
from unittest import mock

import pytest
from werkzeug.datastructures import MultiDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app  # noqa: E402

PRESETS = ('linear', 'linear_type5_segids', 'live_event', 'scte_logger')
FEATURES = ('boundary_handling', 'eidr_routing', 'id3_writing')
LINEAR_FAMILY = ('linear', 'linear_type5_segids')
HELPER = '_handle_time_signal_ad_breaks'

# Issue #6 repro: two Linear-family methods with disjoint pair sets.
TWO_LINEAR_FORM = {
    'include_linear': 'on',
    'channel_group_linear': 'linear_foxnow',
    'seg_pair_34_35_linear': 'on',
    'include_linear_type5_segids': 'on',
    'channel_group_linear_type5_segids': 'linear_newsmax',
    'seg_pair_50_51_linear_type5_segids': 'on',
}


def render(form: dict) -> str:
    ctx = app.build_context(MultiDict({'plugin_name': 'test', **form}))
    return app.plugin_env.get_template('scte_plugin.py.j2').render(**ctx)


def all_forms():
    """Every non-empty preset subset x every feature subset."""
    for n in range(1, len(PRESETS) + 1):
        for presets in itertools.combinations(PRESETS, n):
            for k in range(len(FEATURES) + 1):
                for features in itertools.combinations(FEATURES, k):
                    form = {f'include_{p}': 'on' for p in presets}
                    form.update({f'feature_{f}': 'on' for f in features})
                    yield pytest.param(form, id='+'.join(presets + features))


def load_plugin(source: str):
    """Exec rendered plugin source as a module with slicer/requests stubbed."""
    slicer = mock.MagicMock(name='slicer')
    slicer.GetState.return_value = 'normal'
    with mock.patch.dict(sys.modules, {'slicer': slicer,
                                       'requests': mock.MagicMock(name='requests')}):
        mod = types.ModuleType('generated_plugin')
        exec(compile(source, '<generated>', 'exec'), mod.__dict__)
    return mod, slicer


def type6_slice_info(seg_id: int) -> dict:
    return {
        'splice_command_type': 6,
        'pts_time': 1_000_000,
        'base64': b'',
        'descriptors': [{'segmentation_type_id': seg_id,
                         'segmentation_duration': 90000 * 30,
                         'segmentation_upid': b''}],
    }


# -----------------------------------------------------------------------------
# Structural checks across every preset/feature combination
# -----------------------------------------------------------------------------

@pytest.mark.parametrize('form', list(all_forms()))
def test_parses_with_no_duplicate_top_level_defs(form):
    tree = ast.parse(render(form))
    names = [n.name for n in tree.body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    dupes = [n for n, c in collections.Counter(names).items() if c > 1]
    assert not dupes, f'top-level names defined more than once: {dupes}'

    has_linear = any(f'include_{p}' in form for p in LINEAR_FAMILY)
    assert names.count(HELPER) == (1 if has_linear else 0)


# -----------------------------------------------------------------------------
# Issue #6 — per-method pair tables
# -----------------------------------------------------------------------------

def _helper_calls_by_method(tree: ast.Module) -> dict[str, list[str]]:
    """Map each top-level def -> the `pairs=` Name passed at each HELPER call."""
    out = {}
    for fn in tree.body:
        if not isinstance(fn, ast.FunctionDef) or fn.name == HELPER:
            continue
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == HELPER):
                kw = {k.arg: k.value for k in node.keywords}
                assert 'pairs' in kw, f'{fn.name} calls {HELPER} without pairs='
                assert isinstance(kw['pairs'], ast.Name)
                out.setdefault(fn.name, []).append(kw['pairs'].id)
    return out


def test_each_linear_method_passes_its_own_pairs():
    tree = ast.parse(render(TWO_LINEAR_FORM))
    calls = _helper_calls_by_method(tree)
    # Linear: Type 6 path only. Type5SegIds: Type 6 path + Type 5 descriptor path.
    assert calls == {
        'LinearFoxnow': ['LINEAR_FOXNOW_AD_PAIRS'],
        'LinearNewsmax': ['LINEAR_NEWSMAX_AD_PAIRS', 'LINEAR_NEWSMAX_AD_PAIRS'],
    }


def test_pair_constants_match_form_selection():
    mod, _ = load_plugin(render(TWO_LINEAR_FORM))
    assert mod.LINEAR_FOXNOW_AD_PAIRS == ((34, 35, 'Break'),)
    assert mod.LINEAR_NEWSMAX_AD_PAIRS == ((50, 51, 'Distributor Advertisement'),)


@pytest.mark.parametrize('method, seg_id, expect_ad_start', [
    ('LinearFoxnow', 34, True),     # own pair — was silently dropped pre-fix
    ('LinearFoxnow', 50, False),    # NewsMax's pair — was wrongly honored pre-fix
    ('LinearNewsmax', 50, True),
    ('LinearNewsmax', 34, False),
])
def test_runtime_dispatch_honors_only_own_pairs(method, seg_id, expect_ad_start):
    mod, slicer = load_plugin(render(TWO_LINEAR_FORM))
    mod.SLICER_CONFIG_DICT['scte_ad_break_mode'] = 'time_signal'

    getattr(mod, method)(type6_slice_info(seg_id), 'slicer-1')

    assert slicer.AdStart.called is expect_ad_start
    logged = ' '.join(str(c) for c in slicer.SlicerLogger.call_args_list)
    assert 'Exception' not in logged


def test_helper_without_pairs_takes_no_action():
    mod, slicer = load_plugin(render({'include_linear': 'on'}))
    info = type6_slice_info(34)
    getattr(mod, HELPER)(info, 'slicer-1', [34], [0], info['descriptors'], 1_000_000)
    assert not slicer.AdStart.called


def test_single_linear_method_keeps_default_pairs():
    mod, _ = load_plugin(render({'include_linear': 'on'}))
    assert mod.LINEAR_AD_PAIRS == (
        (34, 35, 'Break'),
        (48, 49, 'Provider Advertisement'),
        (54, 55, 'Distributor Placement Opportunity'),
    )


def test_duplicate_channel_group_rejected():
    resp = app.app.test_client().post('/generate', data={
        'plugin_name': 'test',
        'include_linear': 'on', 'channel_group_linear': 'same',
        'include_live_event': 'on', 'channel_group_live_event': 'same',
    })
    assert resp.status_code == 400
    assert b'Duplicate channel_group' in resp.data


# -----------------------------------------------------------------------------
# Lint gate on rendered output
# -----------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which('ruff') is None, reason='ruff not installed')
def test_ruff_clean_on_rendered_samples(tmp_path):
    """
    E9 = syntax errors; F811 = redefinition of unused name.

    Note F811 alone would NOT have caught issue #6 — the first helper def
    is "used" by the method above it, so ruff sees no unused redefinition.
    test_parses_with_no_duplicate_top_level_defs is the real guard.
    """
    for i, param in enumerate(all_forms()):
        (tmp_path / f'sample_{i}.py').write_text(render(param.values[0]))
    result = subprocess.run(
        ['ruff', 'check', '--no-cache', '--select', 'E9,F811', str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

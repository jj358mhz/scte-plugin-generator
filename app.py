"""
scte-plugin-generator — Flask app.

Skeleton form. POST /generate renders the plugin templates against form
input, packages the result into an in-memory zip, and returns it as a
download. This first cut renders an empty zip so the pipeline can be
proven end-to-end before we wire in the real templates.
"""

import io
import os
import re
import zipfile
from datetime import date
from typing import Any

from flask import Flask, render_template, request, send_file, abort
from jinja2 import Environment, FileSystemLoader, StrictUndefined

GENERATOR_VERSION = '0.3.3'  # bump on meaningful generator changes

app = Flask(__name__)

# -----------------------------------------------------------------------------
# Jinja environment for PLUGIN template rendering.
#
# Separate from Flask's default env — Flask's is for HTML pages, this one is
# for the generated Python/Markdown files. Different roots, different config:
#
#   trim_blocks=True         — strip the newline after a {% %} block
#   lstrip_blocks=True       — strip leading whitespace on lines that start
#                              with a {% %} block
#   keep_trailing_newline=True — preserve the final newline of each template
#   undefined=StrictUndefined  — raise on any undefined variable rather than
#                              silently rendering an empty string
# -----------------------------------------------------------------------------
plugin_env = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates', 'plugin')),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)


# =============================================================================
# Helpers
# =============================================================================

_SNAKE_RE = re.compile(r'^[a-z][a-z0-9_]*$')


def snake_to_pascal(s: str) -> str:
    """
    Convert snake_case to PascalCase.

    'live_event' -> 'LiveEvent'
    'cbs_sports_unified' -> 'CbsSportsUnified'  (no acronym awareness)

    Acronym cases (CBS, NBC, etc.) need the user to override via the form's
    "method name override" field — we can't infer them from the snake string.
    """
    return ''.join(w.capitalize() for w in s.split('_') if w)


def parse_methods_from_form(form) -> list[dict[str, str]]:
    """
    Extract selected methods from POSTed form data.

    For the linear preset, also captures:
        seg_id_pairs (list[tuple]) — which Type 6 seg_id pairs to handle.
        Defaults to (34/35, 48/49, 54/55) if no pairs selected.

    Returns:
        list of {'preset', 'channel_group', 'name', ...} dicts.
    """
    methods = []
    for preset in ('linear', 'live_event', 'scte_logger'):
        if form.get(f'include_{preset}') != 'on':
            continue
        channel_group = (form.get(f'channel_group_{preset}') or preset).strip()
        if not _SNAKE_RE.match(channel_group):
            raise ValueError(
                f'Invalid channel_group for {preset}: {channel_group!r} — '
                f'must be snake_case (lowercase, digits, underscores)'
            )
        name_override = (form.get(f'method_name_{preset}') or '').strip()
        name = name_override or snake_to_pascal(channel_group)
        entry = {
            'preset': preset,
            'channel_group': channel_group,
            'name': name,
        }
        if preset == 'linear':
            pairs = []
            if form.get('seg_pair_32_33') == 'on':
                pairs.append((32, 33, 'Chapter'))
            if form.get('seg_pair_34_35') == 'on':
                pairs.append((34, 35, 'Break'))
            if form.get('seg_pair_48_49') == 'on':
                pairs.append((48, 49, 'Provider Advertisement'))
            if form.get('seg_pair_54_55') == 'on':
                pairs.append((54, 55, 'Distributor Placement Opportunity'))
            # Default: 34/35 + 48/49 + 54/55 if nothing selected
            if not pairs:
                pairs = [
                    (34, 35, 'Break'),
                    (48, 49, 'Provider Advertisement'),
                    (54, 55, 'Distributor Placement Opportunity'),
                ]
            entry['seg_id_pairs'] = pairs
        methods.append(entry)
    return methods


def parse_features_from_form(form) -> set[str]:
    """
    Extract feature flags from POSTed form data.

    Expected form fields:
        feature_boundary_handling   (checkbox)
        feature_eidr_routing        (checkbox)
        feature_id3_writing         (checkbox)

    Returns:
        set of feature name strings.
    """
    features: set[str] = set()
    for feature in ('boundary_handling', 'eidr_routing', 'id3_writing'):
        if form.get(f'feature_{feature}') == 'on':
            features.add(feature)
    return features


def build_context(form) -> dict[str, Any]:
    """
    Build the Jinja render context from form input.

    Adds the `has_linear` / `has_live_event` / `has_oon` derived booleans so
    templates can use the short `{% if has_live_event %}` form instead of
    iterating `methods` inline.
    """
    methods = parse_methods_from_form(form)
    if not methods:
        raise ValueError('At least one method must be selected')

    features = parse_features_from_form(form)

    return {
        'plugin_name':   (form.get('plugin_name') or 'plugin').strip(),
        'client_name':   (form.get('client_name') or 'Client').strip(),
        'author':        (form.get('author') or 'Uplynk').strip(),
        'version':       (form.get('version') or '0.0.1').strip(),
        'today':         date.today().isoformat(),
        'methods':       methods,
        'features':      features,
        'has_linear':      any(m['preset'] == 'linear'      for m in methods),
        'has_live_event':  any(m['preset'] == 'live_event'  for m in methods),
        'has_oon':         False,  # oon preset removed from form; scaffolding kept dormant for future
        'has_scte_logger': any(m['preset'] == 'scte_logger' for m in methods),
        'generator_version': GENERATOR_VERSION,
    }

# =============================================================================
# Routes
# =============================================================================

@app.route('/', methods=['GET'])
def index():
    """Serve the plugin-generation form."""
    return render_template('form.html', generator_version=GENERATOR_VERSION)


@app.route('/generate', methods=['POST'])
def generate():
    """
    Render templates against form input, package into zip, return as download.

    Returns 400 on validation errors, 500 on template render failures.
    """
    try:
        context = build_context(request.form)
    except ValueError as e:
        return f'<pre>Form error: {e}</pre>', 400

    plugin_name = context['plugin_name']

    try:
        plugin_source = plugin_env.get_template('scte_plugin.py.j2').render(**context)
        conf_source = plugin_env.get_template('example.conf.j2').render(**context)
    except Exception as e:
        # Surface Jinja errors to the browser so we can debug template issues
        # in-place during development. Once stable, this can become a 500.
        import traceback
        return (
            f'<pre>Template render failed:\n\n{e}\n\n{traceback.format_exc()}</pre>',
            500,
        )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{plugin_name}/scte_{plugin_name}.py', plugin_source)
        zf.writestr(f'{plugin_name}/uplynk.conf', conf_source)
    buf.seek(0)

    return send_file(
        buf,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'{plugin_name}.zip',
    )


@app.route('/healthz', methods=['GET'])
def healthz():
    """Liveness probe for Portainer/Caddy healthchecks."""
    return {'status': 'ok', 'generator_version': GENERATOR_VERSION}, 200


# =============================================================================
# Entrypoint
# =============================================================================

if __name__ == '__main__':
    # Development server only. In the container, gunicorn drives the app.
    app.run(host='0.0.0.0', port=5000, debug=True)

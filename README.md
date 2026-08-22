# 📺 scte-plugin-generator

🏭 A Flask + Jinja2 web app that generates hardened SCTE-35 plugin scaffolds for the [Uplynk LiveSlicer](https://www.uplynk.com/) from a web form.

- 🌐 **Deployed:** [plugin.telcomjj.com](https://plugin.telcomjj.com) (LAN-only)
- 📦 **Stack:** Flask + gunicorn in Docker, fronted by Caddy, managed by Portainer
- 🚀 **Deploy:** GitOps — push to `main` triggers automatic redeploy
- 🏷️ **Current version:** see [CHANGELOG.md](./CHANGELOG.md)

---

## 📖 Table of contents

- [🎯 What this does](#-what-this-does)
- [👥 User guide](#-user-guide)
  - [🚀 Quickstart](#-quickstart)
  - [🎬 Available presets](#-available-presets)
  - [🎛️ Available features](#-available-features)
  - [📦 What you get](#-what-you-get)
- [🧑‍💻 Developer guide](#-developer-guide)
  - [🏗️ Architecture](#-architecture)
  - [📂 Repo layout](#-repo-layout)
  - [🐳 Local development](#-local-development)
  - [🚀 Deployment](#-deployment)
  - [🔌 Extending the generator](#-extending-the-generator)
- [📚 Background](#-background)

---

## 🎯 What this does

Uplynk's LiveSlicer accepts a Python plugin to handle SCTE-35 signaling — the messages in a broadcast stream that mark ad breaks, program boundaries, slate transitions, and other lifecycle events. Every customer's SCTE-35 workflow is slightly different: some want linear ad insertion, others need Disney-style live event lifecycle handling, others need pure diagnostic logging to characterize a new feed.

🛠️ This generator emits a hardened, production-ready plugin scaffold from a web form. Pick your presets and features, submit, and get back a zip containing:

- 🐍 The plugin (`scte_<plugin_name>.py`)
- ⚙️ A reference `uplynk.conf`
- 📖 A generated README with end-user + developer docs
- 📋 A generated CHANGELOG

📡 Templates are modeled on real production plugins from Disney, CNBC, P1Media, Fox, and Everpass — including hardening patterns like leak-safe SCTE message summaries, float-based exec-time comparisons, config parsing helpers, and redacted API key logging.

---

# 👥 User guide

## 🚀 Quickstart

1. 🌐 Open [plugin.telcomjj.com](https://plugin.telcomjj.com) (LAN-only).
2. 📝 Fill in the form:
   - **Plugin name** (snake_case)
   - **Client name**
   - **Author**
   - **Version** (start at `0.0.1`)
   - ☑️ Check the preset(s) you want (linear, live_event, scte_logger)
   - ☑️ Check optional feature(s) (boundary_handling, eidr_routing, id3_writing)
3. ⬇️ Click **Generate** — a zip downloads.
4. 📤 Deploy per the generated README's instructions.

## 🎬 Available presets

### 📺 `linear`
Standard linear ad-insertion. Fires ad-break start/end on configurable SCTE-35 segmentation descriptor pairs (34/35, 48/49, 54/55 by default). Use for standard commercial broadcast feeds.

### 🎥 `live_event`
Disney-style live event lifecycle. Handles program start/end, mid-event slate breakaways and resumes, and provider placement opportunities. Types 0/16/17/19/20/54/55. Use for live sports, awards shows, or any feed where program boundaries matter more than fixed ad breaks.

### 🔍 `scte_logger`
Diagnostic-only. Logs every SCTE-35 message received without firing any ad breaks. Covers all standardized segmentation type_ids (0x00–0x51) plus graceful fallback for customer-defined types. Use to characterize a new customer's SCTE feed before picking a production preset.

## 🎛️ Available features

- 🚧 **`boundary_handling`** — adds `AdStart`/`AdEnd` boundary signaling around SCTE-driven breaks
- 🗺️ **`eidr_routing`** — routes ad decisioning by EIDR extracted from the SCTE-35 UPID field
- 🏷️ **`id3_writing`** — writes ID3 tags into the outbound stream keyed on SCTE-35 events

## 📦 What you get

A zip named `<plugin_name>.zip` containing:

```text
<plugin_name>/
├── scte_<plugin_name>.py    # the plugin itself
├── uplynk.conf              # reference slicer config, active sections match your selections
├── README.md                # end-user deploy guide + developer docs + SCTE-35 refresher
└── CHANGELOG.md             # seeded with an initial-release entry
```

All hardening patterns are baked in: config parsing helpers, leak-safe message summaries, HOST/PROC_ID discovery, uppercase log-level normalization, redacted apikey in log output. See the generated plugin's own README for full details.

---

# 🧑‍💻 Developer guide

## 🏗️ Architecture

```text
┌──────────────┐   POST /generate    ┌──────────────┐   render(**context)   ┌──────────────┐
│   Browser    │ ──────────────────▶ │   Flask app  │ ────────────────────▶ │  Jinja       │
│  (form.html) │                     │   (app.py)   │                       │  templates/  │
└──────────────┘                     └──────┬───────┘                       └──────┬───────┘
                                            │                                      │
                                            │  build in-memory zip                 │
                                            │  ◀────────────────────────────────────
                                            ▼
                                     ┌──────────────┐
                                     │ send_file()  │
                                     │  as zip DL   │
                                     └──────────────┘
```

The generator itself is deliberately small:

- **`app.py`** — Flask app with two routes (`/`, `/generate`) plus `/healthz`. `build_context()` parses form input into the Jinja context; `generate()` renders every template and packs the results into an in-memory zip.
- **`templates/form.html`** — the HTML form. Renders through Flask's default Jinja env.
- **`templates/plugin/*.j2`** — the plugin scaffold templates. Renders through a separate Jinja env with `StrictUndefined` + `trim_blocks`.

## 📂 Repo layout

```text
scte-plugin-generator/
├── app.py                          # Flask app + form parser + zip builder
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .github/workflows/deploy.yml    # GitOps: SSH to Pi, pull, rebuild
├── static/style.css
├── templates/
│   ├── form.html                   # the input form
│   └── plugin/                     # emitted-plugin templates
│       ├── scte_plugin.py.j2       # master template — sections + entrypoints + method includes
│       ├── _log_helpers.py.j2      # seg-type table + log() helpers (always emitted)
│       ├── _method_linear.py.j2
│       ├── _method_live_event.py.j2
│       ├── _method_scte_logger.py.j2
│       ├── example.conf.j2         # reference uplynk.conf
│       ├── README.md.j2            # generated plugin's README
│       └── CHANGELOG.md.j2         # generated plugin's CHANGELOG
├── README.md                       # this file
└── CHANGELOG.md
```

## 🐳 Local development

```bash
# Clone
git clone git@github.com:jj358mhz/scte-plugin-generator.git
cd scte-plugin-generator

# Install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python app.py
# → http://localhost:5000
```

Or via Docker:

```bash
docker compose up --build
# → http://localhost:8080
```

The dev server auto-reloads on template + code changes. `StrictUndefined` will raise on any undefined variable, so template bugs surface immediately in the browser (with a stack trace) rather than silently rendering empty strings.

## 🚀 Deployment

Push to `main` → GitHub Action SSHes to `telcomjj.com:2222` → `git pull && docker compose up -d --build` → live in ~90 seconds.

Prerequisites on the Pi (one-time):
```bash
cd ~/git/scte-plugin-generator
git config pull.rebase false
git config pull.ff only
```
(Without this, `git pull origin main` fails with `fatal: Cannot rebase onto multiple branches`.)

The stack runs on the `auth-net` Docker network, is managed by Portainer with `restart: unless-stopped`, and is fronted by Caddy for TLS. LAN-only via Pi-hole CNAME.

## 🔌 Extending the generator

### ➕ Add a new preset

1. Write `templates/plugin/_method_<preset>.py.j2` with the new method body.
2. Add an include reference in `templates/plugin/scte_plugin.py.j2`'s methods loop.
3. Add `<preset>` to the preset tuple in `parse_methods_from_form()` in `app.py`.
4. Add a tile to `templates/form.html` for the new preset checkbox + name/channel_group overrides.
5. Update `build_context()` if you need a new `has_<preset>` derived boolean.
6. Add a section to `templates/plugin/example.conf.j2` for any new config keys.
7. Add a preset description to `templates/plugin/README.md.j2`.
8. Bump MINOR version.

### 🎛️ Add a new feature flag

1. Add the feature name to the tuple in `parse_features_from_form()` in `app.py`.
2. Add a checkbox to `templates/form.html`.
3. Gate the relevant plugin code with `{% if '<feature>' in features %}` in `templates/plugin/scte_plugin.py.j2` or a method file.
4. Add config keys to `templates/plugin/example.conf.j2` (active if selected, commented otherwise).
5. Document in `templates/plugin/README.md.j2`.
6. Bump MINOR version.

### 🏷️ Version bump policy

- **PATCH** — cosmetic fixes, small bugfixes, deploy infra changes
- **MINOR** — new template shipped, new preset, new feature, meaningful capability change
- **MAJOR** — `1.0.0` reserved for the complete G-series shipped + all zip files present

Update `GENERATOR_VERSION` at the top of `app.py`. This value is passed into every generated file's footer, so users can trace what generator version built their plugin.

---

## 📚 Background

📖 [SCTE-35](https://webstore.ansi.org/standards/scte/ansiscte352022) is the SMPTE standard for carrying ad-insertion and program-boundary cues in an MPEG transport stream. Every commercial broadcast feed uses it. The messages carry a command type (`splice_null`, `splice_insert`, `time_signal`, etc.) and optional segmentation descriptors that mark the semantic meaning of an event (Program Start, Break End, Provider Placement Opportunity Start, and so on).

📡 The Uplynk LiveSlicer receives SCTE-35 on its input, hands parsed messages to a Python plugin, and expects the plugin to call slicer APIs (`slicer.SetAdMeta()`, `slicer.SlicerLogger()`, etc.) as side effects to actually fire ad breaks, slates, and boundary signals. Every customer's plugin is a variation on the same theme — this generator captures the common hardening patterns and lets us stamp out new customer plugins in minutes instead of days.

---

_Built by [Jeff Johnston](https://github.com/jj358mhz) for [Uplynk](https://www.uplynk.com/) solutions work._

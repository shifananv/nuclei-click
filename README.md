# Nuclei-CLICK

A browser dashboard for [Nuclei](https://github.com/projectdiscovery/nuclei) that
replaces manual YAML/CLI usage with a click-to-select template catalog,
one-click sync of the official template repo, custom template upload, and
live scan output.

**Only scan targets you own or have explicit written authorization to test.**
Nuclei is an active scanner; running it against systems you don't control
without permission is illegal in most jurisdictions and against the terms of
virtually every hosting provider.

## Architecture

```
nuclei-gui/
  backend/
    main.py              FastAPI app (REST + WebSocket)
    template_manager.py  Syncs/parses templates (official repo + uploads)
    scanner.py           Runs the nuclei binary, streams JSONL results
    requirements.txt
  frontend/
    index.html / style.css / app.js   Plain JS dashboard, no build step
  data/
    nuclei-templates/    git clone of the official templates (created on sync)
    custom_templates/    your uploaded .yaml templates
    scans/                per-scan raw JSONL output
```

The backend does not reimplement scanning logic — it shells out to the real
`nuclei` binary, so you get the same engine and template compatibility as
the CLI tool, just with a GUI in front of it.

## 1. Install nuclei itself

The GUI is a wrapper; it needs the actual `nuclei` binary on PATH.

**Option A — Go install (if you have Go 1.21+):**
```bash
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

**Option B — prebuilt binary (Windows/macOS/Linux):**
Download the release for your OS from
https://github.com/projectdiscovery/nuclei/releases and put the binary
somewhere on your PATH.

Verify:
```bash
nuclei -version
```

## 2. Run the backend

```bash
cd nuclei-gui/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** — that's the whole app; FastAPI serves the
frontend directly, so there's no separate frontend server or build step.

## 3. First-time template load

Click **"Sync official templates"** in the sidebar. This runs
`git clone --depth 1` of `projectdiscovery/nuclei-templates` (several
thousand templates, ~100MB) into `data/nuclei-templates/`. Subsequent
clicks run `git pull` to update. You can also drag in your own `.yaml`
template via **"Upload custom template"** — it's parsed and added to the
same searchable catalog immediately.

## 4. Using it

1. Enter a target (URL or IP) you're authorized to scan.
2. Click templates in the catalog to select them — filter by search text,
   severity, tag, or source (official/custom) first if the list is long.
3. Click **Run Scan**. Findings stream into the console and finding cards
   in real time over a WebSocket as nuclei reports them.
4. Raw JSONL for every scan is saved under `data/scans/<scan_id>.jsonl` and
   retrievable via `GET /api/scan/{scan_id}/results`.


## Disclaimer

This repository is intended strictly for educational, research, and authorized security testing purposes only.

Any tools, techniques, proof-of-concept code, or information provided here should only be used on systems, applications, or environments for which you have explicit authorization.

The author assumes no responsibility or liability for any misuse, damage, data loss, unauthorized access, or legal consequences resulting from the use of this repository or its contents.

By using this repository, you acknowledge that you are solely responsible for your actions and agree to comply with all applicable laws, regulations, and responsible disclosure practices.

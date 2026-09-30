# Nuclei GUI

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

## Deploying it somewhere persistent

This was built and tested in a sandboxed environment with no outbound
networking, so I can't stand up a live URL for you — but the project is a
completely standard FastAPI app and deploys anywhere Python runs:

- **A VPS (DigitalOcean/Linode/EC2/etc.):** copy the folder over, follow
  step 2 above, then put it behind `nginx` + a systemd service, or run it
  under `tmux`/`screen` for a quick test. Since nuclei performs active
  scanning, keep this on a box you control and firewalled to trusted IPs —
  don't expose it to the open internet without authentication in front of it.
- **Docker:** a minimal `Dockerfile` — install Python deps, install the
  nuclei binary in the image (Option B above), `COPY` the project, `CMD
  ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]`. Happy to
  write this out fully if you want to containerize it.
- **Windows machine:** steps in "2. Run the backend" work as-is (that's
  what the `venv\Scripts\activate` line is for).

## Extending it (ideas for your project write-up)

- Auth (even basic HTTP auth) before exposing this beyond localhost
- Scan history page (list past `scan_id`s with target/date/finding count)
- Scheduled/recurring scans
- Export findings to PDF/CSV report
- Template favorites/collections for repeat engagements
- Rate-limiting/concurrency controls passed through to nuclei's own
  `-rate-limit` / `-c` flags, exposed as GUI settings

"""
template_manager.py

Handles two sources of Nuclei templates:
  1. The official projectdiscovery/nuclei-templates repo (cloned/pulled via git)
  2. User-uploaded custom .yaml/.yml templates

Parses each template's YAML "info" block so the frontend can show a
searchable, filterable, clickable catalog instead of raw file paths.
"""

import os
import subprocess
import uuid
from pathlib import Path
from typing import Optional

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OFFICIAL_DIR = DATA_DIR / "nuclei-templates"          # git clone target
CUSTOM_DIR = DATA_DIR / "custom_templates"              # user uploads
OFFICIAL_REPO_URL = "https://github.com/projectdiscovery/nuclei-templates.git"

CUSTOM_DIR.mkdir(parents=True, exist_ok=True)

# In-memory cache: id -> template metadata dict. Rebuilt on sync/upload/startup.
_CACHE: dict[str, dict] = {}


def sync_official_templates() -> dict:
    """Clone the official templates repo if absent, otherwise `git pull`."""
    if OFFICIAL_DIR.exists() and (OFFICIAL_DIR / ".git").exists():
        result = subprocess.run(
            ["git", "-C", str(OFFICIAL_DIR), "pull", "--ff-only"],
            capture_output=True, text=True, timeout=300,
        )
    else:
        OFFICIAL_DIR.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", OFFICIAL_REPO_URL, str(OFFICIAL_DIR)],
            capture_output=True, text=True, timeout=300,
        )

    if result.returncode != 0:
        return {"ok": False, "error": result.stderr.strip()}

    count = rebuild_cache()
    return {"ok": True, "templates_loaded": count}


def _parse_template_file(path: Path, source: str) -> Optional[dict]:
    """Extract the bits of a Nuclei template useful for a GUI listing."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            doc = yaml.safe_load(f)
    except Exception:
        return None

    if not isinstance(doc, dict):
        return None

    info = doc.get("info", {}) or {}
    template_id = doc.get("id") or path.stem

    classification = info.get("classification", {}) or {}

    return {
        "id": template_id,
        "path": str(path),
        "source": source,                       # "official" | "custom"
        "name": info.get("name", template_id),
        "author": info.get("author", "unknown"),
        "severity": (info.get("severity") or "unknown").lower(),
        "description": info.get("description", ""),
        "tags": [t.strip() for t in str(info.get("tags", "")).split(",") if t.strip()],
        "cve_id": classification.get("cve-id"),
        "reference": info.get("reference", []),
    }


def rebuild_cache() -> int:
    """Walk both template directories and refresh the in-memory catalog."""
    _CACHE.clear()

    for root, source in ((OFFICIAL_DIR, "official"), (CUSTOM_DIR, "custom")):
        if not root.exists():
            continue
        for path in root.rglob("*.yaml"):
            meta = _parse_template_file(path, source)
            if meta:
                _CACHE[meta["id"]] = meta
        for path in root.rglob("*.yml"):
            meta = _parse_template_file(path, source)
            if meta:
                _CACHE[meta["id"]] = meta

    return len(_CACHE)


def list_templates(search: str = "", severity: str = "", tag: str = "", source: str = "") -> list[dict]:
    if not _CACHE:
        rebuild_cache()

    results = list(_CACHE.values())

    if search:
        s = search.lower()
        results = [
            t for t in results
            if s in t["name"].lower() or s in t["id"].lower() or s in t["description"].lower()
        ]
    if severity:
        results = [t for t in results if t["severity"] == severity.lower()]
    if tag:
        results = [t for t in results if tag.lower() in [x.lower() for x in t["tags"]]]
    if source:
        results = [t for t in results if t["source"] == source]

    return sorted(results, key=lambda t: (t["severity"], t["name"]))


def get_template_paths(template_ids: list[str]) -> list[str]:
    if not _CACHE:
        rebuild_cache()
    return [_CACHE[tid]["path"] for tid in template_ids if tid in _CACHE]


def all_tags() -> list[str]:
    if not _CACHE:
        rebuild_cache()
    tags = set()
    for t in _CACHE.values():
        tags.update(t["tags"])
    return sorted(tags)


def save_custom_template(filename: str, content: bytes) -> dict:
    """Save an uploaded YAML template and validate it parses."""
    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(filename).name}"
    dest = CUSTOM_DIR / safe_name
    dest.write_bytes(content)

    meta = _parse_template_file(dest, "custom")
    if meta is None:
        dest.unlink(missing_ok=True)
        return {"ok": False, "error": "File is not a valid Nuclei YAML template"}

    _CACHE[meta["id"]] = meta
    return {"ok": True, "template": meta}

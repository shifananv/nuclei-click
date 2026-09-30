"""
scanner.py

Wraps the `nuclei` CLI binary. Builds the command from GUI selections
(target + chosen template files) and streams JSONL output line-by-line
so the frontend can show live results instead of waiting for the whole
scan to finish.

Requires the `nuclei` binary to be installed and on PATH.
See README.md for install instructions.
"""

import asyncio
import json
import shutil
import uuid
from pathlib import Path
from typing import AsyncGenerator

BASE_DIR = Path(__file__).resolve().parent.parent
SCANS_DIR = BASE_DIR / "data" / "scans"
SCANS_DIR.mkdir(parents=True, exist_ok=True)


def nuclei_available() -> bool:
    return shutil.which("nuclei") is not None


async def run_scan(target: str, template_paths: list[str]) -> AsyncGenerator[dict, None]:
    """
    Launches nuclei against `target` restricted to `template_paths`,
    yielding one dict per line of output (JSONL findings, or status/error
    events). Also writes the raw findings to a per-scan results file.
    """
    if not nuclei_available():
        yield {"event": "error", "message": "nuclei binary not found on PATH. See README install steps."}
        return

    if not template_paths:
        yield {"event": "error", "message": "No templates selected."}
        return

    scan_id = uuid.uuid4().hex[:12]
    result_file = SCANS_DIR / f"{scan_id}.jsonl"

    cmd = ["nuclei", "-target", target, "-jsonl", "-silent"]
    for tpl in template_paths:
        cmd += ["-t", tpl]

    yield {"event": "started", "scan_id": scan_id, "command": " ".join(cmd)}

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    with open(result_file, "w", encoding="utf-8") as out_f:
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            out_f.write(line + "\n")
            try:
                finding = json.loads(line)
                yield {"event": "finding", "scan_id": scan_id, "data": finding}
            except json.JSONDecodeError:
                yield {"event": "log", "scan_id": scan_id, "message": line}

    stderr_bytes = await proc.stderr.read()
    returncode = await proc.wait()

    if returncode != 0 and stderr_bytes:
        yield {"event": "log", "scan_id": scan_id, "message": stderr_bytes.decode("utf-8", errors="ignore")[-2000:]}

    yield {"event": "finished", "scan_id": scan_id, "returncode": returncode}


def load_scan_results(scan_id: str) -> list[dict]:
    result_file = SCANS_DIR / f"{scan_id}.jsonl"
    if not result_file.exists():
        return []
    findings = []
    with open(result_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return findings

#!/usr/bin/env python3
"""Read-only upstream monitor for the Hermes Baby Monitor fork."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CRITICAL = {
    "baby_monitor/config.yaml", "baby_monitor/run.sh", "baby_monitor/Dockerfile",
    ".github/workflows/release.yaml", ".github/workflows/release.yml",
}

def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True, stderr=subprocess.DEVNULL).strip()

def api_json(url: str):
    try:
        req = Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "hermes-baby-monitor-monitor"})
        with urlopen(req, timeout=10) as response:
            return json.load(response)
    except Exception:
        return None

def main() -> int:
    subprocess.run(["git", "-C", str(ROOT), "fetch", "--quiet", "--prune", "upstream"], check=True)
    head = git("rev-parse", "HEAD")
    upstream = git("rev-parse", "upstream/main")
    base = git("merge-base", "HEAD", "upstream/main")
    new_count = int(git("rev-list", "--count", f"{base}..upstream/main") or "0")
    upstream_paths = set(filter(None, git("diff", "--name-only", f"{base}..upstream/main").splitlines()))
    local_paths = set(filter(None, git("diff", "--name-only", f"upstream/main..HEAD").splitlines()))
    critical_upstream = sorted(upstream_paths & CRITICAL)
    local_patch = bool(local_paths & {"baby_monitor/config.yaml", "baby_monitor/run.sh", "baby_monitor/Dockerfile", "baby_monitor/apparmor.txt"})
    tags = sorted(git("ls-remote", "--tags", "--refs", "upstream").splitlines())
    tag_names = [line.rsplit("refs/tags/", 1)[-1] for line in tags]
    releases = api_json("https://api.github.com/repos/victoriano/home-assistant-baby-monitor/releases?per_page=20") or []
    release_names = sorted({r.get("tag_name", "") for r in releases if r.get("tag_name")})
    ghcr = api_json("https://ghcr.io/v2/victoriano/home-assistant-baby-monitor/tags/list?n=100") or {}
    image_tags = sorted(set(ghcr.get("tags", []))) if isinstance(ghcr, dict) else []
    interesting_tags = sorted({t for t in tag_names + release_names + image_tags if t in {"0.4.0", "latest"} or t.startswith("0.4.") or t.startswith("0.5.")})
    if new_count == 0 and not interesting_tags:
        return 0
    risk = "alto" if critical_upstream else ("medio" if new_count else "basso")
    action = "sync" if new_count else "review"
    print("Baby Monitor upstream update")
    print(f"{new_count} nuovi commit / nuova release {', '.join(release_names[-3:]) if release_names else 'nessuna'}")
    print(f"Patch locali coinvolte: {'sì' if local_patch else 'no'}")
    print(f"Rischio conflitto: {risk}")
    print(f"Azione consigliata: {action}")
    if critical_upstream:
        print("File critici upstream modificati: " + ", ".join(critical_upstream))
    if interesting_tags:
        print("Tag/release/immagini rilevanti: " + ", ".join(interesting_tags))
    print(f"HEAD locale: {head[:12]} | upstream/main: {upstream[:12]}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Monitor upstream non disponibile: comando git fallito ({exc.returncode})", file=sys.stderr)
        raise SystemExit(2)

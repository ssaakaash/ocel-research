#!/usr/bin/env python3
"""Download the public sources listed in realdata/sources.json into realdata/raw/<id>/.

Each source gets its own directory, files are verified against the Zenodo MD5
and size when available, SHA-256 is recorded, and a SOURCE.md is written.
Run with ``python3 -I realdata/src/fetch_sources.py [source_id ...]``.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
UA = {"User-Agent": "team1-ocel-study/0.1 (academic research; contact via repository)"}


def get_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def stream(url: str, dest: Path, max_bytes: int | None = None, attempts: int = 5) -> tuple[str, str, int]:
    """Download with retries; a stalled socket resumes from the partial file via an HTTP Range request."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.unlink(missing_ok=True)
    for attempt in range(1, attempts + 1):
        have = tmp.stat().st_size if tmp.exists() else 0
        headers = dict(UA, **({"Range": f"bytes={have}-"} if have else {}))
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r, tmp.open("ab" if have and r.status == 206 else "wb") as out:
                if have and r.status != 206:
                    have = 0
                while chunk := r.read(1 << 20):
                    have += len(chunk)
                    if max_bytes and have > max_bytes:
                        tmp.unlink(missing_ok=True)
                        raise SystemExit(f"{dest.name}: exceeded size cap of {max_bytes} bytes; aborted")
                    out.write(chunk)
            break
        except (TimeoutError, OSError) as exc:
            print(f"  attempt {attempt}/{attempts} failed at {have / 1e6:.1f} MB ({exc.__class__.__name__}); retrying", flush=True)
            if attempt == attempts:
                raise
    md5, sha = hashlib.md5(), hashlib.sha256()
    with tmp.open("rb") as h:
        while chunk := h.read(1 << 20):
            md5.update(chunk); sha.update(chunk)
    size = tmp.stat().st_size
    tmp.replace(dest)
    return md5.hexdigest(), sha.hexdigest(), size


def fetch_zenodo(src: dict, out_dir: Path) -> list[dict]:
    rec = get_json(f"https://zenodo.org/api/records/{src['record']}")
    index = {f["key"]: f for f in rec.get("files", [])}
    rows = []
    for name in src["files"]:
        meta = index.get(name)
        if meta is None:
            raise SystemExit(f"{src['id']}: {name} not listed in record {src['record']}")
        url = meta.get("links", {}).get("self") or f"https://zenodo.org/api/records/{src['record']}/files/{urllib.parse.quote(name)}/content"
        dest = out_dir / name
        print(f"[{src['id']}] {name} ({meta['size'] / 1e6:.1f} MB) ...", flush=True)
        md5, sha, size = stream(url, dest)
        expected = meta.get("checksum", "").split(":", 1)[-1]
        if size != meta["size"] or (expected and md5 != expected):
            dest.unlink(missing_ok=True)
            raise SystemExit(f"{src['id']}: {name} failed integrity check (size {size} vs {meta['size']}, md5 {md5} vs {expected})")
        rows.append({"file": name, "bytes": size, "sha256": sha, "md5_verified": bool(expected)})
    return rows


def fetch_url(src: dict, out_dir: Path) -> list[dict]:
    dest = out_dir / src["save_as"]
    print(f"[{src['id']}] {src['save_as']} (size unknown, cap {src['max_bytes'] / 1e6:.0f} MB) ...", flush=True)
    _, sha, size = stream(src["url"], dest, src.get("max_bytes"))
    return [{"file": src["save_as"], "bytes": size, "sha256": sha, "md5_verified": False}]


def write_source_md(src: dict, out_dir: Path, rows: list[dict]) -> None:
    lines = [
        f"# {src['id']}", "", f"- Title: {src['title']}", f"- Creators: {src['creators']}",
        f"- DOI: {src['doi']}", f"- Licence: {src['license']}", f"- Nature: {src.get('nature', '')}",
        f"- Retrieved: {date.today().isoformat()}", f"- URL: {src.get('url') or 'https://zenodo.org/records/' + src['record']}", "",
        "| file | bytes | sha256 | Zenodo md5 verified |", "|---|---:|---|---|",
    ]
    lines += [f"| {r['file']} | {r['bytes']} | `{r['sha256']}` | {r['md5_verified']} |" for r in rows]
    (out_dir / "SOURCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    manifest = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    wanted = set(sys.argv[1:])
    for src in manifest["sources"]:
        if wanted and src["id"] not in wanted:
            continue
        out_dir = RAW / src["id"]
        if (out_dir / "SOURCE.md").exists():
            print(f"[{src['id']}] already present, skipping")
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = fetch_zenodo(src, out_dir) if src["kind"] == "zenodo" else fetch_url(src, out_dir)
        write_source_md(src, out_dir, rows)
        print(f"[{src['id']}] done: {sum(r['bytes'] for r in rows) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()

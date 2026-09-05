"""Search Freesound.org for CC0 sound effects and download them into a
project's public/sfx/ folder.

PHASE 2 helper. Needs FREESOUND_API_KEY (env or .env at the edvid repo root).
Get a free key at https://freesound.org/apiv2/apply/ (no OAuth needed for
this — search + preview download both work with the plain API key/token).

Only CC0 (public domain) results are downloaded — no attribution required,
matching this project's policy of never shipping a sound with unclear
licensing (see references/shortform.md's SFX table). Downloads the HQ mp3
preview (previews need no OAuth, unlike the original uploaded file), then
prints peak dB (ffmpeg volumedetect — never trust a new file's level blind,
see click2.mp3's -25dB history) and duration for each, plus the Freesound id
and author for traceability.

Usage:
    python helpers/freesound_search.py "whoosh" --out-dir <edit>/remotion/public/sfx --count 5
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import requests

SEARCH_URL = "https://freesound.org/apiv2/search/text/"

# Freesound's `license` field is a full URL. CC0 shows up as the Creative
# Commons "publicdomain/zero" deed link; matching substrings rather than an
# exact string survives http/https and trailing-slash variants.
CC0_MARKERS = ("publicdomain/zero", "CC0")


def load_api_key() -> str:
    for candidate in [Path(__file__).resolve().parent.parent / ".env", Path(".env")]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "FREESOUND_API_KEY":
                    return v.strip().strip('"').strip("'")
    v = os.environ.get("FREESOUND_API_KEY", "")
    if not v:
        sys.exit("FREESOUND_API_KEY not found in .env or environment "
                 "(get one at https://freesound.org/apiv2/apply/)")
    return v


def is_cc0(license_url: str) -> bool:
    return any(m in license_url for m in CC0_MARKERS)


def search(query: str, api_key: str, count: int) -> list[dict]:
    params = {
        "query": query,
        "token": api_key,
        "fields": "id,name,previews,license,username,duration,url",
        # over-fetch: not every result is CC0, filtered client-side below
        "page_size": max(1, min(count * 5, 150)),
        "sort": "score",
    }
    resp = requests.get(SEARCH_URL, params=params, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Freesound returned {resp.status_code}: {resp.text[:300]}")
    return resp.json().get("results", [])


def download(url: str, dest: Path) -> None:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)


def slugify(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")[:40]


def peak_db(path: Path) -> str:
    out = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    line = next((l for l in out.splitlines() if "max_volume" in l), "")
    return line.split("max_volume:")[-1].strip() if line else "?"


def main() -> None:
    ap = argparse.ArgumentParser(description="Download CC0 sound effects from Freesound into public/sfx/")
    ap.add_argument("query", help="Search query, e.g. 'whoosh'")
    ap.add_argument("--out-dir", type=Path, required=True, help="Destination folder (e.g. remotion/public/sfx)")
    ap.add_argument("--count", type=int, default=3, help="How many CC0 results to download (default 3)")
    ap.add_argument("--max-duration", type=float, default=6.0,
                    help="Skip results longer than this many seconds (default 6 — an SFX, not a track)")
    args = ap.parse_args()

    api_key = load_api_key()
    results = search(args.query, api_key, args.count)
    if not results:
        sys.exit(f"no results for: {args.query}")

    cc0 = [r for r in results
           if is_cc0(r.get("license", "")) and r.get("duration", 999) <= args.max_duration]
    if not cc0:
        sys.exit(f"no CC0 results (<= {args.max_duration}s) for '{args.query}' among "
                 f"{len(results)} matches — try a different query or raise --max-duration")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(args.query)
    saved = 0
    for i, r in enumerate(cc0[: args.count]):
        previews = r.get("previews", {})
        url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
        if not url:
            continue
        dest = args.out_dir / f"{slug}-{i+1}-fs{r['id']}.mp3"
        try:
            download(url, dest)
        except Exception as e:
            print(f"  x failed {r.get('id')}: {e}")
            continue
        saved += 1
        peak = peak_db(dest)
        print(f"  + {dest.name}  {r.get('duration', 0):.2f}s  peak{peak}  "
              f"CC0 by {r.get('username', '?')}  ({r.get('url', '')})")

    print(f"downloaded {saved}/{min(args.count, len(cc0))} CC0 sound(s) -> {args.out_dir}")
    if saved:
        print("license: CC0 (public domain) - no attribution required, safe for commercial use.")


if __name__ == "__main__":
    main()

"""Register a manually-downloaded music/SFX file into the shared asset
library: copies it into the right canonical folder and appends a row to
references/asset-library.md with duration + peak dB measured by ffmpeg
(never hand-typed — see click2.mp3's -25dB history for why that matters).

This is for files Eduardo sources himself (Pixabay, Mixkit, YouTube Audio
Library, a client's own folder, ...) — NOT the procedurally generated pack in
generate_sfx.py, which needs no source/license bookkeeping.

Usage:
    python helpers/register_asset.py <file> --type music --tags "animado, loja de moda" \
        --source "https://pixabay.com/music/..." --license "Pixabay Content License"

    python helpers/register_asset.py <file> --type sfx --tags "buzina de carro, transição de rua" \
        --source "https://freesound.org/people/.../sounds/12345/" --license CC0
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
LIBRARY_MD = SKILL_ROOT / "references" / "asset-library.md"
DEST_DIRS = {
    "music": SKILL_ROOT / "assets" / "shortform" / "public" / "music",
    "sfx": SKILL_ROOT / "assets" / "shortform" / "public" / "sfx_sourced",
}


def probe(path: Path) -> tuple[float, str]:
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    peak_out = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    line = next((l for l in peak_out.splitlines() if "max_volume" in l), "")
    peak = line.split("max_volume:")[-1].strip() if line else "?"
    return float(dur or 0), peak


def append_row(kind: str, filename: str, dur: float, peak: str, tags: str, source: str, license_: str) -> None:
    text = LIBRARY_MD.read_text(encoding="utf-8")
    heading = "## Music" if kind == "music" else "## SFX"
    row = f"| {filename} | {dur:.2f}s | {peak} | {tags} | {source} | {license_} |\n"
    idx = text.index(heading)
    # insert right after the table header (heading, blank line implied by the
    # header+separator rows already in the file) — append at the END of that
    # section, i.e. right before the next "## " heading or end of file
    next_heading = text.find("\n## ", idx + len(heading))
    insert_at = next_heading if next_heading != -1 else len(text)
    text = text[:insert_at] + row + text[insert_at:]
    LIBRARY_MD.write_text(text, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Register a sourced music/SFX file into the shared library")
    ap.add_argument("file", type=Path, help="Local path to the downloaded file")
    ap.add_argument("--type", choices=["music", "sfx"], required=True)
    ap.add_argument("--tags", required=True, help="Mood/use-case, e.g. 'animado, loja de moda, promo'")
    ap.add_argument("--source", required=True, help="URL where it came from")
    ap.add_argument("--license", required=True, dest="license_", help="e.g. CC0, 'Pixabay Content License'")
    args = ap.parse_args()

    if not args.file.exists():
        sys.exit(f"file not found: {args.file}")

    dest_dir = DEST_DIRS[args.type]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / args.file.name
    if dest.exists():
        sys.exit(f"already registered: {dest} (pick a new name or delete the existing one first)")
    shutil.copy2(args.file, dest)

    dur, peak = probe(dest)
    append_row(args.type, dest.name, dur, peak, args.tags, args.source, args.license_)

    print(f"registered {dest.name}  {dur:.2f}s  peak{peak}  -> {dest}")
    print(f"logged in {LIBRARY_MD}")
    if peak != "?" and float(peak.replace("dB", "").strip() or -99) < -18:
        print(f"  WARNING: peak is quiet ({peak}) — may be inaudible under voice/music, consider a gain pass")


if __name__ == "__main__":
    main()

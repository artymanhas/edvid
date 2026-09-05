"""Mix one SFX/music file into an already-rendered video at an exact time,
via ffmpeg — the reliable escape hatch for when a `sfxCues` entry doesn't
survive Remotion's own compositing (see references/shortform.md's
Anti-patterns: dense compositions with many concurrent <Audio> elements have
been observed to silently drop one; verify presence with a lag-precise
cross-correlation, never just a volumedetect peak — a peak can just be
coincidental speech energy).

This exists because hand-writing the ffmpeg filtergraph is where the mistake
actually happened once: `adelay` takes MILLISECONDS by default, not samples —
passing a sample count unconverted silently pushes the sound minutes past the
end of the video, and every peak-dB check still "looks normal" because
nothing errors. This helper does the ms conversion in one place, tested, so
that mistake can't recur.

Usage:
    python helpers/mix_sfx.py cut.mp4 sfx/applause.mp3 --at 12.48 --volume 0.6 -o final.mp4
    python helpers/mix_sfx.py cut.mp4 trilha.mp3 --at 0 --volume 0.12 --loudnorm -o final.mp4

Re-applies the standard color-tag fix (Remotion's output is full-range/
mis-tagged) and, by default, the final loudnorm pass — pass --no-loudnorm if
the input is already normalized and you're just layering one more sound on
top of an already-delivered file.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    return float(out or 0)


def main() -> None:
    ap = argparse.ArgumentParser(description="Mix an SFX/music file into a video at an exact time (ffmpeg)")
    ap.add_argument("video", type=Path, help="Source video (e.g. Remotion's render.mp4 or an already-delivered cut)")
    ap.add_argument("sfx", type=Path, help="Audio file to mix in (mp3/wav/...)")
    ap.add_argument("--at", type=float, required=True, help="Start time in seconds on the video's timeline")
    ap.add_argument("--volume", type=float, default=0.5, help="Linear gain on the mixed-in sound (default 0.5)")
    ap.add_argument("-o", "--out", type=Path, required=True, help="Output video path")
    ap.add_argument("--loudnorm", dest="loudnorm", action="store_true", default=True)
    ap.add_argument("--no-loudnorm", dest="loudnorm", action="store_false")
    ap.add_argument("--no-color-fix", dest="color_fix", action="store_false", default=True,
                    help="Skip the Remotion full-range/mis-tag correction (pass this for a non-Remotion source)")
    args = ap.parse_args()

    if not args.video.exists():
        sys.exit(f"video not found: {args.video}")
    if not args.sfx.exists():
        sys.exit(f"sfx file not found: {args.sfx}")

    delay_ms = round(args.at * 1000)  # adelay takes MILLISECONDS — the whole point of this file
    duration = ffprobe_duration(args.video)

    vf = ("[0:v]scale=in_range=full:out_range=limited,format=yuv420p,"
          "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv[vid];"
          if args.color_fix else "[0:v]null[vid];")
    af_tail = f"loudnorm=I=-14:TP=-1:LRA=11[out]" if args.loudnorm else "anull[out]"

    filter_complex = (
        f"{vf}"
        f"[1:a]aformat=channel_layouts=stereo,adelay={delay_ms}|{delay_ms},volume={args.volume}[sfx];"
        f"[0:a][sfx]amix=inputs=2:duration=first:normalize=0,{af_tail}"
    )

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(args.video), "-i", str(args.sfx),
        "-filter_complex", filter_complex,
        "-map", "[vid]" if args.color_fix else "0:v", "-map", "[out]",
        "-c:v", "libx264" if args.color_fix else "copy",
    ]
    if args.color_fix:
        cmd += ["-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                "-colorspace", "bt709", "-color_primaries", "bt709",
                "-color_trc", "bt709", "-color_range", "tv"]
    cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-t", f"{duration:.6f}", "-movflags", "+faststart", str(args.out)]

    subprocess.run(cmd, check=True)

    peak = subprocess.run(
        ["ffmpeg", "-i", str(args.out), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    ).stderr
    line = next((l for l in peak.splitlines() if "max_volume" in l), "")
    print(f"mixed {args.sfx.name} at {args.at}s (delay={delay_ms}ms) into {args.out}")
    print(f"  {line.strip()}")
    print("  VERIFY presence with a lag-precise correlation, not just this peak — "
          "see references/shortform.md's Anti-patterns for why a peak alone can mislead.")


if __name__ == "__main__":
    main()

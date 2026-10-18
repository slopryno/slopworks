#!/usr/bin/env python3
"""Screenshots for the visual review step (AAR 2026-10-17, the /work/ incident): every page at 360, 390 and 768,
light and dark, full height, saved under docs/design/review/<pr>/ for Polish and Trial to look at before sign-off.

  python3 scripts/shots.py 80                      -> full set in REVIEW_DIR/80/<theme>-<width>/<page>[.partN].webp,
                                                      plus docs/design/review/80/manifest.json and key/ (committed)
  python3 scripts/shots.py 80 --sheets /tmp/s80    also write contact sheets there (not committed)
  python3 scripts/shots.py 80 --only work/index.html,index.html --key team/index.html

The full set stays out of git (c243: about 42MB per design PR is too much for a public repo). It goes to REVIEW_DIR
(env SLOPWORKS_REVIEW_DIR, default ../slopworks-review next to the repo, on the box that the bots share).
Git gets a small manifest with a SHA-256 for every file, and a few key shots at reduced quality: the first part of
home, work and each --key page at 390, light and dark. scripts/bot.py checks the manifest against the files on disk.

Each full page is cut into parts of at most PART_H pixels, so every file stays far under CI's 1 MB limit and stays
readable at full size. WebP keeps a full review to tens of megabytes. Optional contact sheets put several parts side
by side at half size for a first pass; the full-size parts are the record. Uses the same headless Chrome as scripts/mobile_audit.py; nothing is added to site/.
"""
import argparse, hashlib, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mobile_audit  # noqa: E402

ROOT = mobile_audit.ROOT
WIDTHS = (360, 390, 768)
THEMES = ("light", "dark")
PART_H = 2400
MAX_H = 24000
REVIEW_DIR = Path(os.environ.get("SLOPWORKS_REVIEW_DIR", ROOT.parent / "slopworks-review"))
KEY_PAGES = ("index.html", "work/index.html")
KEY_WIDTH, KEY_H, KEY_Q = 390, 1600, 35


def sha(f):
    return hashlib.sha256(Path(f).read_bytes()).hexdigest()


def manifest(pr, full=None):
    """Every file of the full set with its SHA-256, in a stable order."""
    full = Path(full or REVIEW_DIR / str(pr))
    files = {str(f.relative_to(full)): sha(f) for f in sorted(full.glob("*/*.webp"))}
    return {"pr": int(pr), "widths": list(WIDTHS), "themes": list(THEMES), "count": len(files),
            "bytes": sum((full / f).stat().st_size for f in files), "files": files}


def slug(page):
    return "home" if page == "index.html" else page.replace("/index.html", "").replace(".html", "").replace("/", "_")


def shoot(exe, url, width, height, dark, out):
    with tempfile.TemporaryDirectory() as tmp:
        args = [exe, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", f"--user-data-dir={tmp}/p",
                f"--window-size={width},{height}", f"--screenshot={out}", url]
        if dark:
            args[1:1] = ["--force-dark-mode", "--blink-settings=preferredColorScheme=0"]
        subprocess.run(args, capture_output=True, timeout=120)


def main():
    from PIL import Image  # only needed to shoot; bot.py imports this file for the names
    ap = argparse.ArgumentParser()
    ap.add_argument("pr")
    ap.add_argument("--only", help="comma-separated pages, e.g. work/index.html")
    ap.add_argument("--sheets", help="directory for half-size contact sheets (kept out of the repo)")
    ap.add_argument("--key", default="", help="comma-separated pages to add to the committed key shots")
    a = ap.parse_args()
    exe = mobile_audit.chrome()
    if not exe:
        sys.exit("no Chrome or Chromium found")
    only = a.only.split(",") if a.only else None
    heights = {(r["page"], r["width"]): r.get("doc_h", 2000) for r in mobile_audit.measure(list(WIDTHS), only=only)}
    base = REVIEW_DIR / str(a.pr)
    docs = ROOT / "docs" / "design" / "review" / str(a.pr)
    jobs = []
    with tempfile.TemporaryDirectory() as tmp:
        for (page, w), h in heights.items():
            for theme in THEMES:
                png = Path(tmp) / f"{theme}-{w}-{slug(page)}.png"
                jobs.append((page, w, theme, min(h, MAX_H), png))
        with ThreadPoolExecutor(6) as pool:
            list(pool.map(lambda j: shoot(exe, (mobile_audit.SITE / j[0]).as_uri(), j[1], j[3], j[2] == "dark", j[4]), jobs))
        made = []
        for page, w, theme, h, png in jobs:
            d = base / f"{theme}-{w}"
            d.mkdir(parents=True, exist_ok=True)
            for old in [d / f"{slug(page)}.webp", *d.glob(f"{slug(page)}.part*.webp")]:
                old.unlink(missing_ok=True)  # a page that got shorter must not keep stale parts
            im = Image.open(png).convert("RGB")
            n = (im.height + PART_H - 1) // PART_H
            for i in range(n):
                part = im.crop((0, i * PART_H, im.width, min(im.height, (i + 1) * PART_H)))
                f = d / (f"{slug(page)}.webp" if n == 1 else f"{slug(page)}.part{i + 1}.webp")
                part.save(f, format="WEBP", quality=50, method=6)
                made.append((theme, w, f))
    print(f"{len(made)} screenshot parts in {base}")
    docs.mkdir(parents=True, exist_ok=True)
    m = manifest(a.pr, base)
    (docs / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")
    keyd = docs / "key"
    keyd.mkdir(exist_ok=True)
    for page in list(KEY_PAGES) + [p for p in a.key.split(",") if p]:
        for theme in THEMES:
            d = base / f"{theme}-{KEY_WIDTH}"
            src = d / f"{slug(page)}.webp"
            src = src if src.exists() else d / f"{slug(page)}.part1.webp"
            if src.exists():
                im = Image.open(src).convert("RGB")
                im.crop((0, 0, im.width, min(im.height, KEY_H))).save(keyd / f"{theme}-{KEY_WIDTH}-{slug(page)}.webp", format="WEBP", quality=KEY_Q, method=6)
    print(f"manifest: {m['count']} files, {m['bytes'] // 1024} KB out of git; key shots in {keyd.relative_to(ROOT)}")
    if not a.sheets:
        return
    # contact sheets: up to 8 parts per sheet, half size, in page order
    sheets = Path(a.sheets)
    sheets.mkdir(parents=True, exist_ok=True)
    for theme in THEMES:
        for w in WIDTHS:
            files = [f for t, ww, f in made if t == theme and ww == w]
            for k in range(0, len(files), 8):
                group = [Image.open(f) for f in files[k:k + 8]]
                sw, sh = w // 2, PART_H // 2
                sheet = Image.new("RGB", (len(group) * (sw + 8), sh), "#888")
                for i, im in enumerate(group):
                    sheet.paste(im.resize((sw, im.height // 2)), (i * (sw + 8), 0))
                sheet.save(sheets / f"{theme}-{w}-{k // 8 + 1:02d}.jpg", quality=70, optimize=True)


if __name__ == "__main__":
    main()

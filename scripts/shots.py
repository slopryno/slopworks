#!/usr/bin/env python3
"""Screenshots for the visual review step (AAR 2026-10-17, the /work/ incident): every page at 360, 390 and 768,
light and dark, full height, saved under docs/design/review/<pr>/ for Polish and Trial to look at before sign-off.

  python3 scripts/shots.py 77                      -> docs/design/review/77/<theme>-<width>/<page>[.partN].webp
  python3 scripts/shots.py 77 --sheets /tmp/s77    also write contact sheets there (not committed)
  python3 scripts/shots.py 77 --only work/index.html,index.html

Each full page is cut into parts of at most PART_H pixels, so every file stays far under CI's 1 MB limit and stays
readable at full size. WebP keeps a full review to tens of megabytes. Optional contact sheets put several parts side
by side at half size for a first pass; the full-size parts are the record. Uses the same headless Chrome as scripts/mobile_audit.py; nothing is added to site/.
"""
import argparse, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mobile_audit  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = mobile_audit.ROOT
WIDTHS = (360, 390, 768)
THEMES = ("light", "dark")
PART_H = 2400
MAX_H = 24000


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
    ap = argparse.ArgumentParser()
    ap.add_argument("pr")
    ap.add_argument("--only", help="comma-separated pages, e.g. work/index.html")
    ap.add_argument("--sheets", help="directory for half-size contact sheets (kept out of the repo)")
    a = ap.parse_args()
    exe = mobile_audit.chrome()
    if not exe:
        sys.exit("no Chrome or Chromium found")
    only = a.only.split(",") if a.only else None
    heights = {(r["page"], r["width"]): r.get("doc_h", 2000) for r in mobile_audit.measure(list(WIDTHS), only=only)}
    base = ROOT / "docs" / "design" / "review" / str(a.pr)
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
            im = Image.open(png).convert("RGB")
            n = (im.height + PART_H - 1) // PART_H
            for i in range(n):
                part = im.crop((0, i * PART_H, im.width, min(im.height, (i + 1) * PART_H)))
                f = d / (f"{slug(page)}.webp" if n == 1 else f"{slug(page)}.part{i + 1}.webp")
                part.save(f, format="WEBP", quality=50, method=6)
                made.append((theme, w, f))
    print(f"{len(made)} screenshot parts in {base.relative_to(ROOT)}")
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

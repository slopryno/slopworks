#!/usr/bin/env python3
"""Measured mobile and UX audit (i36, i37). Loads every built page in headless Chrome at phone, tablet, and desktop
widths and counts what breaks, so the team works from numbers, not guesses.

The measuring harness is a temporary HTML file outside site/ (the site itself stays script-free). Chrome loads each
page in an iframe of the exact width, and the harness reads layout from it. Static numbers (nav items, taps from home,
page weight, reduced-motion coverage) come from the built files in Python.

  python3 scripts/mobile_audit.py                 full audit as JSON on stdout
  python3 scripts/mobile_audit.py --widths 360    one width only (what the CI test runs)
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
FOLD = {360: 640, 390: 844, 414: 896, 768: 1024, 1280: 800}  # viewport heights used for "above the fold"
KEY_PAGES = ["timeline/", "cases/", "arena/", "challenges/", "team/", "lessons/", "chat/", "team/xp/", "team/forge/", "updates/", "schedule/"]
MIN_TAP = 44

HARNESS = r"""<!doctype html><meta charset="utf-8"><body style="margin:0"><pre id="out">running</pre><script>
const JOBS = %s, MIN = %d, out = [];
function bg(el, w){ for(;el;el=el.parentElement){const c=w.getComputedStyle(el).backgroundColor; if(c && !/rgba\(0, 0, 0, 0\)|transparent/.test(c)) return c;} return 'rgb(255, 255, 255)'; }
function rgb(s){ const m=s.match(/[\d.]+/g).map(Number); return m.slice(0,3); }
function lum(c){ const v=c.map(x=>{x/=255; return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4)}); return .2126*v[0]+.7152*v[1]+.0722*v[2]; }
function ratio(a,b){ const x=lum(rgb(a)), y=lum(rgb(b)); return (Math.max(x,y)+.05)/(Math.min(x,y)+.05); }
function inlineLink(a){ // WCAG 2.5.5 "Inline": a link inside a sentence or block of text is exempt; list rows and nav links are not
  if (a.tagName !== 'A') return false;
  let b = a.parentElement; while (b && /^(SPAN|STRONG|EM|SMALL|B|I|CODE|TIME)$/.test(b.tagName)) b = b.parentElement;
  if (!b) return false;
  let linkText = 0; b.querySelectorAll('a').forEach(x => linkText += (x.textContent||'').trim().length);
  const other = (b.textContent||'').replace(/\s+/g,' ').trim().length - linkText;
  if (/^(P|BLOCKQUOTE|DD|FIGCAPTION)$/.test(b.tagName)) return other > 0;
  return other >= 25; }
let W0 = null; function w0(el){ return W0.getComputedStyle(el); }
function measure(frame, job){
  const w = frame.contentWindow, d = frame.contentDocument; W0 = w;
  const vw = d.documentElement.clientWidth, r = {page: job.page, width: job.width};
  r.overflow_px = Math.max(0, d.documentElement.scrollWidth - vw);
  r.overflow_by = []; if (r.overflow_px) d.querySelectorAll('body *').forEach(el => { const b = el.getBoundingClientRect();
    if ((b.right > vw + 1 || (el.scrollWidth > el.clientWidth + 1 && w.getComputedStyle(el).overflowX === 'visible' && el.children.length === 0)) && r.overflow_by.length < 5)
      r.overflow_by.push(el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(' ')[0] : '') + ' ' + (el.textContent||'').trim().slice(0, 30) + ' ' + Math.round(b.right)); });
  let small = [], inl = 0, total = 0, area = {header: 0, main: 0, footer: 0};
  d.querySelectorAll('a[href], button, summary, label, input, select, [role=button]').forEach(el => {
    const b = el.getBoundingClientRect(); if (b.width === 0 || b.height === 0 || w.getComputedStyle(el).visibility === 'hidden') return;
    if (el.closest('[hidden]') || el.closest('.skip')) return;
    if (el.closest('details:not([open])') && el.tagName !== 'SUMMARY' && !el.closest('summary')) return;
    total++;
    if (inlineLink(el)) { inl++; return; }
    if (b.width < MIN || b.height < MIN) { area[el.closest('header') ? 'header' : el.closest('footer') ? 'footer' : 'main']++; small.push((el.tagName + ' ' + (el.textContent||'').trim()).slice(0, 40) + ' ' + Math.round(b.width) + 'x' + Math.round(b.height)); }
  });
  r.targets = total; r.small_targets = small.length; r.small_examples = small.slice(0, 40); r.small_by_area = area; r.inline_links = inl;
  let minFont = 99, tiny = 0, maxChars = 0, lowContrast = 0, words = 0;
  const texts = d.querySelectorAll('main p, main li, main td, main th, main h1, main h2, main h3, main summary, main span, main time, header a, footer p');
  texts.forEach(el => { const cs = w.getComputedStyle(el), b = el.getBoundingClientRect(); if (!b.width || !(el.textContent||'').trim()) return;
    const fs = parseFloat(cs.fontSize); minFont = Math.min(minFont, fs); if (fs < 12) tiny++;
    if (el.tagName === 'P') maxChars = Math.max(maxChars, Math.round(b.width / (fs * 0.5)));
    if (ratio(cs.color, bg(el, w)) < 4.5 && !el.closest('a')) lowContrast++; });
  const tw = d.createTreeWalker(d.body, NodeFilter.SHOW_TEXT); let n;
  while ((n = tw.nextNode())) { const p = n.parentElement; if (!p || p.closest('[hidden], .skip, details:not([open]) > :not(summary)')) continue;
    const rg = d.createRange(); rg.selectNodeContents(n); const b = rg.getBoundingClientRect();
    if (b.height && b.top < job.fold && b.bottom > 0) words += (n.textContent.match(/\S+/g) || []).length; }
  r.min_font_px = minFont === 99 ? null : minFont; r.tiny_text = tiny; r.max_line_chars = maxChars; r.low_contrast = lowContrast; r.words_above_fold = words;
  const nav = d.querySelector('header'); r.header_px = nav ? Math.round(nav.getBoundingClientRect().height) : 0;
  let tables = 0, wide = 0, wideUnscrolled = 0;
  d.querySelectorAll('main table').forEach(t => { tables++; const p = t.parentElement;
    if (t.scrollWidth > vw || t.getBoundingClientRect().right > vw + 1) { wide++; let s = t.parentElement, ok = false;
      for (; s && s !== d.body; s = s.parentElement) { const ox = w.getComputedStyle(s).overflowX; if (ox === 'auto' || ox === 'scroll') { ok = true; break; } }
      if (!ok) wideUnscrolled++; } });
  r.tables = tables; r.wide_tables = wide; r.wide_tables_unscrolled = wideUnscrolled;
  // Visual-defect checks added after the 2026-10-17 /work/ incident (AAR): the metric audit missed mid-word breaks,
  // element-level overflow, and anything the document's scrollWidth doesn't report.
  const scroller = el => { for (let s = el; s && s !== d.documentElement; s = s.parentElement) { const ox = w.getComputedStyle(s).overflowX; if (ox === 'auto' || ox === 'scroll') return s; } return null; };
  const name = el => (el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.split(' ')[0] : '') + ' "' + (el.textContent||'').trim().replace(/\s+/g,' ').slice(0, 30) + '"');
  const shown = el => !el.closest('[hidden], .skip') && !(el.closest('details:not([open])') && !el.closest('summary'));
  let midword = [], boxes = [], past = [], narrow = [];
  const tw2 = d.createTreeWalker(d.body, NodeFilter.SHOW_TEXT); let tn;
  while ((tn = tw2.nextNode())) { const p = tn.parentElement; if (!p || !shown(p)) continue;
    { const all = d.createRange(); all.selectNodeContents(tn); const rr = all.getBoundingClientRect();  // text can spill past its box
      if (rr.width && rr.right > vw + 1 && !scroller(p) && past.length < 20) past.push('text in ' + name(p) + ' right edge ' + Math.round(rr.right) + ' > ' + vw); }
    const re = /[^\s\-\u2013\u2014\/]+/g, s = tn.textContent; let m;
    while ((m = re.exec(s))) { if (m[0].length < 2) continue;
      const rg = d.createRange(); rg.setStart(tn, m.index); rg.setEnd(tn, m.index + m[0].length);
      const rs = [...rg.getClientRects()].filter(x => x.width > 0); if (rs.length < 2) continue;
      if (Math.abs(rs[rs.length - 1].top - rs[0].top) < 2) continue;  // same line, split by markup only
      const natural = rs.reduce((a, x) => a + x.width, 0);
      let a0 = m.index, b0 = m.index + m[0].length; while (a0 > 0 && !/\s/.test(s[a0 - 1])) a0--; while (b0 < s.length && !/\s/.test(s[b0])) b0++;
      const token = s.slice(a0, b0);  // the whole space-free run: a URL, path, or email is allowed to break between its parts
      if (natural > 0.75 * vw || (/[@\/]/.test(token) && token.length >= 20)) continue;  // too long for any phone line: breaking is right
      if (midword.length < 20) midword.push('"' + m[0] + '" in ' + name(p) + ' split over ' + rs.length + ' lines'); } }
  d.querySelectorAll('body *').forEach(el => { if (!shown(el)) return; const cs = w.getComputedStyle(el); if (cs.display === 'none' || cs.display === 'contents') return;
    const b = el.getBoundingClientRect(); if (!b.width && !b.height) return;
    const inScroll = scroller(el.parentElement);
    if (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1 && cs.overflowX !== 'auto' && cs.overflowX !== 'scroll' && !inScroll && boxes.length < 20)
      boxes.push(name(el) + ' scrollWidth ' + el.scrollWidth + ' > clientWidth ' + el.clientWidth);
    if (b.right > vw + 1 && !inScroll && past.length < 20) past.push(name(el) + ' right edge ' + Math.round(b.right) + ' > ' + vw);
    const lines = () => { const rg = d.createRange(); rg.selectNodeContents(el); return new Set([...rg.getClientRects()].filter(x => x.width > 0).map(x => Math.round(x.top))).size; };
    if (cs.display !== 'inline' && el.children.length === 0 && (el.textContent||'').trim().length >= 6 && el.clientWidth > 0 && el.clientWidth < 3 * parseFloat(cs.fontSize) && lines() > 1 && narrow.length < 20)
      narrow.push(name(el) + ' only ' + el.clientWidth + 'px wide'); });
  r.doc_h = d.documentElement.scrollHeight;
  r.midword_breaks = midword; r.box_overflow = boxes; r.past_right_edge = past; r.narrow_text = narrow;
  return r;
}
let i = 0; const f = document.createElement('iframe'); f.style.border = '0'; document.body.appendChild(f);
function next(){ if (i >= JOBS.length) { document.getElementById('out').textContent = JSON.stringify(out); return; }
  const j = JOBS[i++]; f.style.width = j.width + 'px'; f.style.height = j.fold + 'px';
  f.onload = () => { try { if (j.font) { const st = f.contentDocument.createElement('style'); st.textContent = 'body,body *{font-family:' + j.font + ' !important}'; f.contentDocument.head.appendChild(st); f.contentDocument.body.offsetHeight; } out.push(measure(f, j)); } catch (e) { out.push({page: j.page, width: j.width, error: String(e)}); } next(); };
  f.src = j.url; }
next();
</script>"""


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links, self.nav, self.depth = [], 0, 0
    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "header": self.depth = 1
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if self.depth: self.nav += 1
    def handle_endtag(self, tag):
        if tag == "header": self.depth = 0


def pages():
    return sorted(str(p.relative_to(SITE)) for p in SITE.rglob("*.html"))


def resolve(page, href):
    if href.startswith(("http", "mailto:", "#")): return None
    path = os.path.normpath(os.path.join(os.path.dirname(page), href.split("#")[0])) if href.split("#")[0] else page
    if path == ".": path = "index.html"
    if not path.endswith(".html"): path = path.rstrip("/") + "/index.html"
    return path


def static_numbers():
    out, graph = {}, {}
    css = sum(p.stat().st_size for p in SITE.glob("*.css"))
    for k in pages():
        html = (SITE / k).read_text()
        p = Links(); p.feed(html)
        graph[k] = {t for t in (resolve(k, h) for h in p.links) if t}
        avatars = set(re.findall(r'assets/avatars/(\w+)\.svg', html))
        av = sum((SITE / f"assets/avatars/{a}.svg").stat().st_size for a in avatars if (SITE / f"assets/avatars/{a}.svg").exists())
        head = html[html.find("<header"):html.find("</header>")]
        nav_items = sum(len(re.findall(r"<a ", n)) for n in re.findall(r"<nav\b.*?</nav>", head, re.S))
        out[k] = {"nav_items": nav_items, "html_bytes": len(html.encode()), "page_bytes": len(html.encode()) + css + av, "avatar_bytes": av, "avatars": len(avatars)}
    dist, todo = {"index.html": 0}, ["index.html"]
    while todo:
        k = todo.pop(0)
        for t in graph.get(k, ()):
            if t not in dist and t in graph:
                dist[t] = dist[k] + 1; todo.append(t)
    taps = {kp: dist.get(kp + "index.html") for kp in KEY_PAGES}
    css_text = "".join(p.read_text() for p in SITE.glob("*.css"))
    mq = re.findall(r"@media\s*\(([^)]*)\)", css_text)
    return {"pages": out, "taps_from_home": taps, "css_bytes": css,
            "media_queries": {"max_width": sum("max-width" in q for q in mq), "min_width": sum("min-width" in q for q in mq)},
            "animations": len(re.findall(r"animation\s*:", css_text)), "reduced_motion_rules": len(re.findall(r"prefers-reduced-motion", css_text)),
            "avatar_svgs_without_reduced_motion": sum("prefers-reduced-motion" not in p.read_text() for p in (SITE / "assets/avatars").glob("*.svg"))}


def chrome():
    for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if shutil.which(c): return shutil.which(c)
    return None


def measure(widths, dark=False, only=None, font=None):
    exe = chrome()
    if not exe: raise RuntimeError("no Chrome or Chromium found")
    jobs = [{"page": k, "width": w, "fold": FOLD.get(w, 800), "url": (SITE / k).as_uri(), "font": font} for w in widths for k in (only or pages())]
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "harness.html"
        h.write_text(HARNESS % (json.dumps(jobs), MIN_TAP))
        args = [exe, "--headless", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files", "--hide-scrollbars",
                f"--user-data-dir={tmp}/profile", "--virtual-time-budget=60000", "--dump-dom", h.as_uri()]
        if dark: args[1:1] = ["--force-dark-mode", "--blink-settings=preferredColorScheme=0"]
        dom = subprocess.run(args, capture_output=True, text=True, timeout=240).stdout
    m = re.search(r'<pre id="out">(.*?)</pre>', dom, re.S)
    if not m or m.group(1).strip() == "running": raise RuntimeError("the harness didn't finish")
    import html as h2
    return json.loads(h2.unescape(m.group(1)))


def summary(rows):
    by = {}
    for r in rows:
        s = by.setdefault(r["width"], {"pages": 0, "overflowing_pages": 0, "small_targets": 0, "pages_with_small_targets": 0, "inline_links": 0,
                                       "tiny_text": 0, "low_contrast": 0, "wide_tables_unscrolled": 0, "tables": 0, "max_line_chars": 0, "errors": 0})
        if "error" in r: s["errors"] += 1; continue
        s["pages"] += 1; s["overflowing_pages"] += r["overflow_px"] > 0; s["small_targets"] += r["small_targets"]
        s["pages_with_small_targets"] += r["small_targets"] > 0; s["inline_links"] += r["inline_links"]; s["tiny_text"] += r["tiny_text"]
        s["low_contrast"] += r["low_contrast"]; s["wide_tables_unscrolled"] += r["wide_tables_unscrolled"]; s["tables"] += r["tables"]
        s["max_line_chars"] = max(s["max_line_chars"], r["max_line_chars"])
        for k in ("midword_breaks", "box_overflow", "past_right_edge", "narrow_text"):
            s[k] = s.get(k, 0) + len(r.get(k, []))
    return by


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--widths", default="360,390,414,768,1280")
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--font", help='force a font, e.g. "DejaVu Sans" (wide) to stress-test text that only fits in the default font')
    a = ap.parse_args()
    rows = measure([int(w) for w in a.widths.split(",")], a.dark, font=a.font)
    print(json.dumps({"summary": summary(rows), "static": static_numbers(), "rows": rows}, indent=1))

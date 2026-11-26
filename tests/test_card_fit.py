"""Open flip cards stay inside the deck strip: no page-width overflow (mobile UX playbook 2026-10-31).
Replaces the old :target fullscreen fit check. Measured in headless Chrome on the built Team page."""
import json, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import mobile_audit  # noqa: E402

SIZES = [(390, 844), (360, 780), (1280, 800)]
HARNESS = r"""<!doctype html><meta charset="utf-8"><body style="margin:0"><pre id="out">running</pre><script>
const SIZES = %s, URL = %s, out = []; let i = 0; const f = document.createElement('iframe'); f.style.border = '0'; document.body.appendChild(f);
function next(){ if (i >= SIZES.length) { document.getElementById('out').textContent = JSON.stringify(out); return; }
  const [w, h] = SIZES[i++]; f.style.width = w + 'px'; f.style.height = h + 'px';
  f.onload = () => { const win = f.contentWindow, d = f.contentDocument;
    const flips = [...d.querySelectorAll('details.flip')];
    for (const det of flips) { det.open = true; }
    const sw = Math.max(d.documentElement.scrollWidth, d.body.scrollWidth);
    out.push({size: w + 'x' + h, overflow: Math.max(0, sw - w), open: flips.length});
    for (const det of flips) { det.open = false; }
    next(); };
  f.src = URL + '?' + i; }
next();
</script>"""


class OpenCardsFitThePhone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        exe = mobile_audit.chrome()
        if not exe:
            raise AssertionError("CI needs headless Chrome for the card fit check")
        with tempfile.TemporaryDirectory() as tmp:
            h = Path(tmp) / "harness.html"
            h.write_text(HARNESS % (json.dumps(SIZES), json.dumps((ROOT / "site/team/index.html").as_uri())))
            dom = subprocess.run([exe, "--headless", "--disable-gpu", "--no-sandbox", "--allow-file-access-from-files", "--hide-scrollbars",
                                  f"--user-data-dir={tmp}/profile", "--virtual-time-budget=30000", "--dump-dom", h.as_uri()],
                                 capture_output=True, text=True, timeout=180).stdout
        m = re.search(r'<pre id="out">(.*?)</pre>', dom, re.S)
        import html
        cls.rows = json.loads(html.unescape(m.group(1))) if m and m.group(1).strip() != "running" else []

    def test_every_size_measured(self):
        self.assertEqual(len(self.rows), len(SIZES))

    def test_no_page_overflow_with_a_card_open(self):
        bad = {r["size"]: r["overflow"] for r in self.rows if r["overflow"] > 1}
        self.assertEqual(bad, {})

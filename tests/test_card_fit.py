"""Ryno, Oct 20 8:06 PM ET: "cards do not have to be scrollable on mobile phones". Every open card (19 roles and the CEO)
fits one phone screen with no scrolling inside it, measured in headless Chrome on the built Team page (iframe harness,
outside site/, like scripts/mobile_audit.py). Sizes: 390x844 and 360x780 phones, the same phones with browser bars
(390x664, 360x640), and 320x568."""
import json, re, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import mobile_audit  # noqa: E402

SIZES = [(390, 844), (360, 780), (390, 664), (360, 640), (320, 568)]
HARNESS = r"""<!doctype html><meta charset="utf-8"><body style="margin:0"><pre id="out">running</pre><script>
const SIZES = %s, URL = %s, out = []; let i = 0; const f = document.createElement('iframe'); f.style.border = '0'; document.body.appendChild(f);
function next(){ if (i >= SIZES.length) { document.getElementById('out').textContent = JSON.stringify(out); return; }
  const [w, h] = SIZES[i++]; f.style.width = w + 'px'; f.style.height = h + 'px';
  f.onload = () => { const win = f.contentWindow, d = f.contentDocument;
    for (const o of d.querySelectorAll('.slot .o')) { win.location.hash = o.id; const c = o.parentElement.querySelector('.card'), b = c.getBoundingClientRect();
      out.push({size: w + 'x' + h, card: o.id, over: c.scrollHeight - c.clientHeight, top: Math.round(b.top), bottom: Math.round(b.bottom), vh: win.innerHeight}); }
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

    def test_every_card_measured(self):
        self.assertEqual(len(self.rows), len(SIZES) * len(re.findall(r'class="o" id=', (ROOT / "site/team/index.html").read_text())))

    def test_no_open_card_scrolls(self):
        bad = {f'{r["size"]} {r["card"]}': r["over"] for r in self.rows if r["over"] > 1 or r["top"] < 0 or r["bottom"] > r["vh"]}
        self.assertEqual(bad, {})


if __name__ == "__main__":
    unittest.main()

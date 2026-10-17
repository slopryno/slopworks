"""Trial's tests for Team chat archive rollover: the main page keeps headroom, nothing is dropped, and every link still lands."""
import json, re, sys, unittest
from pathlib import Path
from posixpath import normpath, dirname, join
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check, build  # noqa: E402

FILES = build.build()
CSS = sum(len(v.encode()) for k, v in FILES.items() if k.endswith(".css")) or sum(p.stat().st_size for p in (ROOT / "site").glob("*.css"))
CHAT_PAGES = {k: v for k, v in FILES.items() if k == "chat/index.html" or k.startswith("chat/archive/")}
load = lambda n: json.loads((ROOT / f"data/{n}.json").read_text())


def ids(html):
    return set(re.findall(r'\bid="([^"]+)"', html))


class ChatArchive(unittest.TestCase):
    def test_main_page_keeps_headroom(self):
        size = len(FILES["chat/index.html"].encode()) + CSS
        self.assertLess(size, 0.6 * check.PATTERNS["max_page_bytes"], f"Team chat is {size} bytes")

    def test_every_chat_page_passes_page_checks(self):
        for k, html in CHAT_PAGES.items():
            self.assertEqual(check.a11y_issues(html), [], k)
            self.assertLessEqual(len(html.encode()) + CSS, check.PATTERNS["max_page_bytes"], k)
            self.assertNotIn("<script", html, k)
            self.assertEqual(check.pii_hits(html), [], k)

    def test_nothing_dropped(self):
        where = {}
        for k, html in CHAT_PAGES.items():
            for i in ids(html):
                where.setdefault(i, []).append(k)
        demo = {r["id"] for r in load("research") if r["question"].startswith("Demo challenge")}
        for i in [c["id"] for c in load("chat")] + [x["id"] for x in load("ideas")] + [r["id"] for r in load("research") if r["id"] not in demo]:
            self.assertEqual(len(where.get(i, [])), 1, f"{i} should live on exactly one Team chat page: {where.get(i)}")

    def test_case_links_stay_on_main_page(self):
        main = ids(FILES["chat/index.html"])
        for c in load("cases"):
            for s in c["steps"]:
                if s.get("link", "").startswith("../chat/#"):
                    self.assertIn(s["link"].split("#")[1], main)

    def test_archive_linked_from_main(self):
        for k in CHAT_PAGES:
            if k.startswith("chat/archive/"):
                self.assertIn(f'href="{k[5:]}"', FILES["chat/index.html"])

    def test_every_internal_link_resolves(self):
        pages = {k: v for k, v in FILES.items() if k.endswith(".html")}
        for k, html in pages.items():
            for h in re.findall(r'href="([^"]+)"', html):
                if h.startswith(("http", "mailto:")) or not ("#" in h or h.endswith((".html", "/"))):
                    continue
                path, _, frag = h.partition("#")
                target = k if not path else normpath(join(dirname(k), path))
                if target.endswith("/") or target in (".", "..") or not target.endswith(".html"):
                    target = (target.rstrip("/") + "/index.html").lstrip("./") if target not in (".",) else "index.html"
                target = "index.html" if target in ("/index.html", "index.html") else target
                if target.endswith(".html") and target in pages:
                    if frag and frag != "main":
                        self.assertIn(frag, ids(pages[target]), f"{k}: {h}")
                elif target.endswith(".html") and not (ROOT / "site" / target).exists():
                    self.fail(f"{k}: {h} -> {target} missing")

    def test_feed_links_land(self):
        items = json.loads(FILES["chat.json"])["items"]
        for it in items:
            path, _, frag = it["url"][len(build.BASE):].partition("#")
            page = FILES[path + "index.html" if path.endswith("/") else path]
            if frag:
                self.assertIn(frag, ids(page), it["url"])


if __name__ == "__main__":
    unittest.main()

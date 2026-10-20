#!/usr/bin/env python3
"""Role skills from pinned toolkits (Ryno, 2026-10-19 10:06 PM ET: "Ok have the team level up immediately using pstack and
adding to their profiles"). Standard library only.

  skills.py                 print each role's skills, from bots/*.md
  skills.py --drift DIR     compare data/skills.json's pins with a checkout of cursor/plugins at DIR (the Thursday pstack watch)

Each role file has a **Skills:** block with 1 to 4 lines: - [name](pinned link) (source): how the role uses it.
check.py runs errors(): every listed skill is in data/skills.json, under the source it names, with the link pinned to
that source's commit. A skill nobody uses can't sit in the manifest, and one name can't be both used and skipped.
"""
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_SKILLS, MAX_WORDS = 4, 25
BLOCK = re.compile(r"^\*\*Skills:\*\*[^\n]*\n((?:- [^\n]*\n?)*)", re.M)
LINE = re.compile(r"^- \[(?P<name>[a-z0-9-]+)\]\((?P<url>[^)\s]+)\) \((?P<source>[^)]+)\): (?P<use>\S.*)$")


def link(manifest, source, name):
    """The one link a role file may use for a skill: its directory at the pinned commit."""
    s = manifest["sources"][source]
    return f'{s["repo"]}/tree/{s["commit"][:7]}/{s["path"]}/skills/{name}'


def role_skills(text):
    """[(name, url, source, use)] from a role file's **Skills:** block, or None when it has no block."""
    m = BLOCK.search(text)
    if not m:
        return None
    out = []
    for line in m.group(1).splitlines():
        x = LINE.match(line)
        out.append((x["name"], x["url"], x["source"], x["use"]) if x else (None, line, None, None))
    return out


def load(root=None):
    return json.loads(((root or ROOT) / "data/skills.json").read_text())


def errors(root=None, validate=None):
    root = root or ROOT
    p = root / "data/skills.json"
    if not p.exists():
        return ["data/skills.json is missing (role skills need a pinned manifest)"]
    if validate is None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from check import validate
    try:
        man = json.loads(p.read_text())
    except ValueError as err:
        return [f"data/skills.json: {err}"]
    schema = json.loads((root / "data/schema/skills.schema.json").read_text())
    errs = [f"data/skills.json {e}" for e in validate(man, schema)]
    if errs:
        return errs
    defs = schema["definitions"]
    for kind, key in (("sources", "source"), ("skills", "skill"), ("skipped", "skipped")):
        for n, v in man[kind].items():
            errs += [f"data/skills.json {e}" for e in validate(v, defs[key], f"$.{kind}.{n}")]
    if errs:
        return errs
    for kind in ("skills", "skipped"):
        errs += [f"data/skills.json {kind}.{n}: unknown source {v['source']!r}" for n, v in man[kind].items() if v["source"] not in man["sources"]]
    errs += [f"data/skills.json: {n} is both used and skipped" for n in sorted(set(man["skills"]) & set(man["skipped"]))]
    used = set()
    for f in sorted((root / "bots").glob("*.md")):
        got = role_skills(f.read_text())
        where = f"bots/{f.name}"
        if got is None:
            errs.append(f"{where}: needs a **Skills:** block with 1 to {MAX_SKILLS} skills from data/skills.json")
            continue
        if not 1 <= len(got) <= MAX_SKILLS:
            errs.append(f"{where}: lists {len(got)} skills; the limit is 1 to {MAX_SKILLS}")
        names = [g[0] for g in got]
        errs += [f"{where}: {n} is listed twice" for n in sorted({n for n in names if n and names.count(n) > 1})]
        for name, url, source, use in got:
            if name is None:
                errs.append(f"{where}: skill line isn't '- [name](link) (source): use': {url[:60]}")
                continue
            used.add(name)
            s = man["skills"].get(name)
            if not s:
                errs.append(f"{where}: {name} isn't in data/skills.json" + (" (it's on the skipped list)" if name in man["skipped"] else ""))
                continue
            if source != s["source"]:
                errs.append(f"{where}: {name} is from {s['source']}, not {source}")
            elif url != link(man, source, name):
                errs.append(f"{where}: {name} must link {link(man, source, name)} (the pinned commit)")
            if len(use.split()) > MAX_WORDS:
                errs.append(f"{where}: {name}'s line is {len(use.split())} words; the limit is {MAX_WORDS}")
    errs += [f"data/skills.json: {n} isn't used by any role; remove it or move it to skipped" for n in sorted(set(man["skills"]) - used)]
    return errs


def drift(checkout, root=None):
    """What changed upstream since the pins: [(source, skill, kind)], kind in changed, removed, new."""
    man, out = load(root), []
    for src, s in man["sources"].items():
        d = Path(checkout) / s["path"] / "skills"
        have = {p.name for p in d.iterdir() if (p / "SKILL.md").is_file()} if d.is_dir() else set()
        mine = {n for n, v in man["skills"].items() if v["source"] == src}
        known = mine | {n for n, v in man["skipped"].items() if v["source"] == src}
        for n in sorted(mine):
            if n not in have:
                out.append((src, n, "removed"))
            elif hashlib.sha256((d / n / "SKILL.md").read_bytes()).hexdigest() != man["skills"][n]["sha256"]:
                out.append((src, n, "changed"))
        out += [(src, n, "removed") for n in sorted((known - mine) - have)]
        out += [(src, n, "new") for n in sorted(have - known)]
    return out


def main(argv):
    if argv[:1] == ["--drift"] and len(argv) == 2:
        found = drift(argv[1])
        for src, n, kind in found:
            print(f"{src}: {n} {kind}")
        print(f"{len(found)} drift item(s) against the pins in data/skills.json" if found else "no drift: every pinned skill matches")
        return 1 if found else 0
    for f in sorted((ROOT / "bots").glob("*.md")):
        print(f"{f.stem}: " + ", ".join(g[0] or "?" for g in role_skills(f.read_text()) or []))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

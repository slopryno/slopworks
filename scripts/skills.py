#!/usr/bin/env python3
"""Role skills from pinned toolkits (Ryno, 2026-10-19 10:06 PM ET: "Ok have the team level up immediately using pstack and
adding to their profiles"). Standard library only.

  skills.py                 print each role's skills, from bots/*.md
  skills.py --drift DIR     compare data/skills.json's pins with a checkout of cursor/plugins at DIR (the Thursday pstack watch)

Each role file has a **Skills:** block with 1 to 4 lines: - [name](pinned link) (source): how the role uses it.
check.py runs errors(): every listed skill is in data/skills.json, under the source it names, with the link pinned to
that source's commit. A skill nobody uses can't sit in the manifest, and one name can't be both used and skipped.

Training tracks (Ryno, 2026-10-20 7:05 AM ET: "lets send polish and gamemaster to training. Mobile design and
development. Heavy on UI/UX design principles") live in data/skills.json "tracks": sourced modules, each with a principle,
how it applies here, a practice item and the check that enforces it, plus one graded audit per role. A role in a track
names it in a **Training track:** line; track_errors() checks both sides, the sources and the audit. No XP field exists.
"""
import hashlib, json, re, sys, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAX_SKILLS, MAX_WORDS = 4, 25
BLOCK = re.compile(r"^\*\*Skills:\*\*[^\n]*\n((?:- [^\n]*\n?)*)", re.M)
TRACK = re.compile(r"^\*\*Training track:\*\* `(?P<id>[a-z0-9-]+)`", re.M)
BACKLOG_REF = re.compile(r"^d\d+$")
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


def role_tracks(text):
    """Track ids a role file names in its **Training track:** lines."""
    return TRACK.findall(text)


def track_modules(track, role):
    return [m for m in track["modules"] if role in m["roles"]]


TRACK_HOSTS = ("w3.org", "developer.apple.com", "support.google.com", "developer.android.com", "nngroup.com", "lawsofux.com", "web.dev")


def track_source_error(url):
    """Training sources are the reputable public guides only: https, no query string (tracking), a host on TRACK_HOSTS.
    A fragment may point at one criterion in a long standard (WCAG 2.2's TR page)."""
    u = urllib.parse.urlparse(url)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or u.query:
        return "must be an https link with no query string"
    if not any(host == h or host.endswith("." + h) for h in TRACK_HOSTS):
        return f"host {host} isn't on TRACK_HOSTS"
    return ""


def track_errors(root=None, validate=None):
    """data/skills.json tracks: valid shape, real https sources that a module uses, modules tied to the track's roles and to
    pinned skills, one audit per role graded by another role, findings tied to that role's modules and to real backlog items,
    and a **Training track:** line in exactly the role files the track names."""
    root = root or ROOT
    if validate is None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from check import validate
    man = load(root)
    defs = json.loads((root / "data/schema/skills.schema.json").read_text())["definitions"]
    p = root / "data/design_backlog.json"
    backlog = {d["id"] for d in json.loads(p.read_text())} if p.exists() else set()
    errs, named = [], {}
    for f in sorted((root / "bots").glob("*.md")):
        for t in role_tracks(f.read_text()):
            named.setdefault(t, set()).add(f.stem)
    for tid, t in man.get("tracks", {}).items():
        w = f"data/skills.json tracks.{tid}"
        e = validate(t, defs["track"], f"$.tracks.{tid}")
        if e:
            errs += [f"data/skills.json {x}" for x in e]
            continue
        for k, s in t["sources"].items():
            errs += [f"data/skills.json {x}" for x in validate(s, defs["track_source"], f"$.tracks.{tid}.sources.{k}")]
            why = track_source_error(s.get("url", "")) if isinstance(s, dict) else None
            if why:
                errs.append(f"{w}: source {k} {why}")
        ids, used = [], set()
        for m in t["modules"]:
            e = validate(m, defs["module"], f"$.tracks.{tid}.modules")
            if e:
                errs += [f"data/skills.json {x}" for x in e]
                continue
            ids.append(m["id"])
            used |= set(m["sources"])
            errs += [f"{w} {m['id']}: role {r} isn't in the track" for r in m["roles"] if r not in t["roles"]]
            errs += [f"{w} {m['id']}: unknown source {k}" for k in m["sources"] if k not in t["sources"]]
            errs += [f"{w} {m['id']}: {k} isn't a pinned skill" for k in m.get("skills", []) if k not in man["skills"]]
            if not m["sources"]:
                errs.append(f"{w} {m['id']}: needs at least one source")
        errs += [f"{w}: module {i} is listed twice" for i in sorted({i for i in ids if ids.count(i) > 1})]
        errs += [f"{w}: source {k} isn't used by any module" for k in sorted(set(t["sources"]) - used)]
        if set(t["exercises"]) != set(t["roles"]):
            errs.append(f"{w}: needs exactly one audit per role ({', '.join(t['roles'])})")
        seen = []
        for role, x in t["exercises"].items():
            e = validate(x, defs["exercise"], f"$.tracks.{tid}.exercises.{role}")
            if e:
                errs += [f"data/skills.json {y}" for y in e]
                continue
            if x["grade"]["by"] == role:
                errs.append(f"{w}: {role} can't grade its own audit")
            mine = {m["id"] for m in track_modules(t, role)}
            for g in x["findings"]:
                e = validate(g, defs["finding"], f"$.tracks.{tid}.exercises.{role}.findings")
                if e:
                    errs += [f"data/skills.json {y}" for y in e]
                    continue
                seen.append(g["id"])
                if g["module"] not in mine:
                    errs.append(f"{w}: {role}'s finding {g['id']} cites {g['module']}, which isn't in {role}'s track")
                if BACKLOG_REF.match(g["next"]) and g["next"] not in backlog:
                    errs.append(f"{w}: finding {g['id']} points at {g['next']}, which isn't in data/design_backlog.json")
            if not x["findings"]:
                errs.append(f"{w}: {role}'s audit has no findings")
        errs += [f"{w}: finding {i} is listed twice" for i in sorted({i for i in seen if seen.count(i) > 1})]
        files = {r.lower() for r in t["roles"]}
        errs += [f"bots/{r}.md: needs a **Training track:** `{tid}` line" for r in sorted(files - named.get(tid, set()))]
        errs += [f"bots/{r}.md: names track {tid}, which doesn't list it" for r in sorted(named.get(tid, set()) - files)]
    errs += [f"bots/{r}.md: names unknown track {tid}" for tid in sorted(set(named) - set(man.get("tracks", {}))) for r in sorted(named[tid])]
    return errs


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
        text = f.read_text()
        print(f"{f.stem}: " + ", ".join(g[0] or "?" for g in role_skills(text) or []) + "".join(f" + track {t}" for t in role_tracks(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

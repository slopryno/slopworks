"""Team calendar (Ryno, 2026-10-19 9:34 PM ET: "Make it a real calendar"). Standard library only, no scripts on the page.

data/calendar.json holds one-off dated events and holiday character themes; routines come from data/schedule.json by
schedule_id and are expanded here from their cron. The page is built at build time: the current month and the next two
as tables, with an agenda list for phones, and site/calendar.ics for subscribing. "Today" is the date of the newest run
record (data/state.json), not the clock, so `build.py --check` stays repeatable; the daily run moves it forward.

Holiday avatar sets switch only through active_set(): inside a theme's switch_on..switch_off window, and only once that
theme's ceo-yes event is done. scripts/check.py calendar_errors() holds the plan, design and review rule.
"""
from datetime import date, timedelta
from html import escape

e = lambda s: escape(str(s), quote=True)
DAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
DAY_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
ICS_DAY = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
TYPES = {"holiday-theme": "Holiday theme", "review": "Review", "release": "Release", "research": "Research", "routine": "Routine"}
MONTHS_SHOWN = 3
STEP_ORDER = ["plan", "design", "review"]
RANK = {"plan": 0, "design": 1, "wording": 2, "review": 3, "ceo-yes": 4}  # each step on or after the one before; ceo-yes and review by the switch


def d(s):
    return date.fromisoformat(s)


def nice(x):
    return f"{DAY[x.weekday()]} {MONTH[x.month - 1][:3]}\u00a0{x.day}"


def _field(f, lo, hi):
    """One cron field as a set of ints, or None for '*'. Lists and ranges only (all the schedule uses)."""
    if f == "*":
        return None
    out = set()
    for part in f.split(","):
        a, _, b = part.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    if not out or min(out) < lo or max(out) > hi:
        raise ValueError(f"cron field {f!r} out of range")
    return out


def parse_cron(expr):
    """(day of month, month, weekday Mon=0) sets from 'min hour dom mon dow'. Time is the daily run's, so it's ignored."""
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(f"cron {expr!r} needs 5 fields")
    dom, mon, dow = _field(parts[2], 1, 31), _field(parts[3], 1, 12), _field(parts[4], 0, 7)
    if dow is not None:
        dow = {(x - 1) % 7 for x in dow}  # cron: 0 and 7 are Sunday, 1 is Monday
    return dom, mon, dow


def matches(day, expr):
    """Both day fields restricted means both must hold: '1-7 * 1' is the first Monday, as schedule.json says.
    (Plain cron would OR them; the schedule's own words are the source here.)"""
    dom, mon, dow = parse_cron(expr)
    return ((dom is None or day.day in dom) and (mon is None or day.month in mon) and (dow is None or day.weekday() in dow))


def run_time(sched):
    """The daily run's clock time in words ('4:45 AM ET'), from the daily item's cron, so site copy can't drift from
    the schedule (Ryno, 2026-10-20 10:15 AM ET: "Lets have runs start early morning so visitors can get the latest
    version once they wake up")."""
    item = next(i for i in sched["items"] if i["id"] == "daily")
    minute, hour = (int(x) for x in item["cron"].split()[:2])
    return f"{(hour % 12) or 12}:{minute:02d} {'AM' if hour < 12 else 'PM'} ET"


def cadence(expr):
    """Plain words for a schedule cron: 'Every Monday', 'First Monday of each month', 'Every day'."""
    dom, mon, dow = parse_cron(expr)
    days = " and ".join(DAY_FULL[x] for x in sorted(dow or []))
    if dom == set(range(1, 8)) and dow:
        return f"First {days} of each month"
    return f"Every {days}" if dow else "Every day"


def months(today, n=MONTHS_SHOWN):
    y, m, out = today.year, today.month, []
    for _ in range(n):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def month_end(y, m):
    return (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)


def themes(cal):
    return {t["id"]: t for t in cal["themes"]}


def yes_done(cal, theme_id):
    return any(x.get("theme") == theme_id and x.get("step") == "ceo-yes" and x["status"] == "done" for x in cal["events"])


def start_of(t):
    return max(d(t["switch_on"]), d(t["live_from"])) if t.get("live_from") else d(t["switch_on"])


def active_set(cal, day):
    """The holiday avatar set to show on `day`, or None. The only switch: in the window, and only after Ryno's yes."""
    for t in cal["themes"]:
        if t["status"] != "placeholder" and t.get("avatar_set") and t.get("switch_on") and t.get("switch_off"):
            if d(t["switch_on"]) <= day <= d(t["switch_off"]) and yes_done(cal, t["id"]):
                return t["avatar_set"]
    return None


def dated(cal):
    """One-off events plus the switch-on and switch-back days each scheduled theme implies, sorted by date."""
    out = [dict(id=x["id"], date=d(x["date"]), title=x["title"], owner=x["owner"], type=x["type"], status=x["status"],
                note=x.get("note", ""), with_=list(x.get("with") or []), recurring=False, rank=RANK.get(x.get("step"), 5)) for x in cal["events"]]
    for t in cal["themes"]:
        if t["status"] == "placeholder" or not t.get("switch_on"):
            continue
        ok = yes_done(cal, t["id"])
        cond = "" if ok else " Only after Ryno's yes."
        out.append(dict(id=f'{t["id"]}-on', date=start_of(t), title=f'{t["name"]} blobs on', owner="Coordinator", type="holiday-theme",
                        status="planned", note=f'On the site to {nice(d(t["switch_off"]))}.{cond}', with_=[], recurring=False, rank=6))
        out.append(dict(id=f'{t["id"]}-off', date=d(t["switch_off"]) + timedelta(days=1), title="Everyday blobs back", owner="Coordinator",
                        type="holiday-theme", status="planned", note=f'{t["name"]} set switches off.', with_=[], recurring=False, rank=6))
    return sorted(out, key=lambda x: (x["date"], x["rank"], x["id"]))


def routines(cal, sched):
    by_id = {i["id"]: i for i in sched["items"]}
    return [(r, by_id[r["schedule_id"]]) for r in cal["recurring"] if r["schedule_id"] in by_id]


def recurring(cal, sched, start, end):
    """Routine days from start to end, never before recurring_from: past days show only what's on record."""
    first = max(start, d(cal["recurring_from"]))
    out, day = [], first
    while day <= end:
        for r, item in routines(cal, sched):
            if r["show"] != "note" and matches(day, item["cron"]):
                out.append(dict(id=f'{r["schedule_id"]}-{day.isoformat()}', date=day, title=r["title"], owner=r["owner"], type=r["type"],
                                status="planned", note="", with_=[], recurring=True, show=r["show"], rank=7))
        day += timedelta(days=1)
    return out


def who(x):
    return x["owner"] + (" with " + ", ".join(x["with_"]) if x["with_"] else "")


DONE = '<span aria-hidden="true">\u2713 </span><span class="vh">Done: </span>'


def _cell_item(x):
    cls = f't-{e(x["type"])}' + (" rt" if x["recurring"] else "")
    return f'<li class="{cls}">' + (DONE if x["status"] == "done" else "") + f'{e(x["title"])}</li>'


def _grid(y, m, today, evs):
    first = date(y, m, 1)
    cells = [None] * first.weekday() + [date(y, m, k) for k in range(1, month_end(y, m).day + 1)]
    cells += [None] * (-len(cells) % 7)
    head = "".join(f'<th scope="col"><abbr title="{DAY_FULL[i]}">{DAY[i]}</abbr></th>' for i in range(7))
    rows = []
    for w in range(0, len(cells), 7):
        tds = []
        for c in cells[w:w + 7]:
            if c is None:
                tds.append('<td class="pad"></td>')
                continue
            day = [x for x in evs if x["date"] == c]
            mark = any(not x["recurring"] or x.get("show") == "agenda" for x in day)
            cls = " ".join(k for k, on in (("today", c == today), ("past", c < today), ("ev", mark)) if on)
            items = "".join(_cell_item(x) for x in day)
            attrs = (f' class="{cls}"' if cls else "") + (' aria-current="date"' if c == today else "")
            tds.append(f'<td{attrs}><time datetime="{c.isoformat()}">{c.day}</time>' + (f"<ul>{items}</ul>" if items else "") + "</td>")
        done_wk = all(c is None or c < today for c in cells[w:w + 7]) and not any(x["date"] in cells[w:w + 7] for x in evs)
        rows.append(('<tr class="wk-past">' if done_wk else "<tr>") + "".join(tds) + "</tr>")
    return (f'<div class="scroll"><table class="cal" aria-labelledby="m-{y}-{m:02d}">'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def _agenda_item(x, today):
    """One glance line (date, owner, state) and the title; the note sits behind a tap (Ryno: short leads, details on tap)."""
    state = "Done" if x["status"] == "done" else ("Today" if x["date"] == today else ("Not done yet" if x["date"] < today else ""))
    flag = f'<span class="tag b-yes">{state}</span>' if state else ""
    title = (f'<details><summary>{e(x["title"])}</summary><p>{e(x["note"])}</p></details>' if x["note"] else f'<strong>{e(x["title"])}</strong>')
    return (f'<li class="t-{e(x["type"])}"><span class="when"><time datetime="{x["date"].isoformat()}">{nice(x["date"])}</time>'
            f'<span>{e(who(x))}</span>{flag}</span>{title}</li>')


# Inline, so the shared style.css (and every other page's weight) doesn't grow. Mobile first: phones get day numbers with a
# dot for dated events, then the agenda; from 48rem each day shows its events; from 64rem the agenda sits beside the grid.
CSS = ("<style>.cal-month .vh{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%);white-space:nowrap}"
       ".cal{table-layout:fixed;width:100%!important;max-width:none!important}"
       ".cal th,.cal td{min-width:0!important;padding:.3rem .2rem;vertical-align:top;text-align:center}"
       ".cal th{font-size:.75rem;color:var(--muted);font-weight:600}.cal abbr{text-decoration:none}.cal td{height:2.6rem;position:relative}"
       ".cal time{display:inline-flex;align-items:center;justify-content:center;width:1.8rem;height:1.8rem;border-radius:50%;font-variant-numeric:tabular-nums}"
       ".cal .past time{color:var(--muted)}.cal .today time{background:var(--fg);color:var(--bg);font-weight:700}"
       ".cal .ev::after{content:\"\";position:absolute;left:50%;bottom:.2rem;width:.35rem;height:.35rem;margin-left:-.175rem;border-radius:50%;background:var(--accent)}"
       ".cal ul{display:none;list-style:none;margin:.2rem 0 0;padding:0}"
       ".agenda{list-style:none;padding:0;margin:.75rem 0 1.5rem}.agenda li{padding:.3rem 0 .3rem .75rem;border-left:2px solid var(--line);margin:0 0 .5rem}"
       ".agenda .when{display:flex;flex-wrap:wrap;gap:.25rem .6rem;align-items:center;font-size:.8rem;color:var(--muted);font-variant-numeric:tabular-nums}"
       ".agenda strong,.agenda summary{display:block;padding:.65rem 0;line-height:1.5;font-size:1rem;font-weight:600;color:var(--fg)}.agenda summary{cursor:pointer;list-style:none}"
       ".agenda summary::-webkit-details-marker{display:none}.agenda summary::after{content:\"+\";margin-left:.4rem;color:var(--muted);font-weight:400}.agenda details[open] summary::after{content:\"\\2212\"}"
       ".agenda details p{margin:0 0 .4rem;color:var(--muted)}"
       ".t-holiday-theme{border-left-color:var(--accent)!important}.t-release{border-left-color:var(--ok)!important}.t-review{border-left-color:var(--warn)!important}"
       "@media (min-width:48rem){.cal td{height:6.5rem;text-align:left;padding:.35rem}.cal th{text-align:left;padding-left:.45rem}.cal .ev::after{display:none}"
       ".cal ul{display:block}.cal li{font-size:.75rem;line-height:1.3;margin:0 0 .2rem;padding-left:.3rem;border-left:2px solid var(--line);overflow-wrap:anywhere}"
       ".cal li.rt{color:var(--muted)}.cal .wk-past td{height:2.6rem}}"
       "@media (min-width:64rem){.cal-month{display:grid;grid-template-columns:minmax(0,2fr) minmax(15rem,1fr);gap:0 2rem;align-items:start}"
       ".cal-month h2{grid-column:1/-1}.cal-month .agenda{margin-top:0}.cal td{height:6rem}.cal .wk-past td{height:2.6rem}}</style>")


def render(cal, sched, today, up="../"):
    win = months(today)
    start, end = date(*win[0], 1), month_end(*win[-1])
    one_off = dated(cal)
    evs = sorted([x for x in one_off if start <= x["date"] <= end] + recurring(cal, sched, today + timedelta(days=1), end),
                 key=lambda x: (x["date"], x["rank"], x["id"]))
    weekly = [r for r, _ in routines(cal, sched) if r["show"] == "grid"]
    daily = [r for r, _ in routines(cal, sched) if r["show"] == "note"]
    out = [CSS, f'<p class="links"><a href="{up}calendar.ics">Subscribe (.ics)</a></p>']
    for y, m in win:
        mine = [x for x in evs if (x["date"].year, x["date"].month) == (y, m)]
        listed = [x for x in mine if not x["recurring"] or x.get("show") == "agenda"]
        agenda = ('<ol class="agenda">' + "".join(_agenda_item(x, today) for x in listed) + "</ol>") if listed else '<p class="empty">No dated events this month.</p>'
        out.append(f'<section class="cal-month" aria-labelledby="m-{y}-{m:02d}"><h2 id="m-{y}-{m:02d}">{MONTH[m - 1]} {y}</h2>{_grid(y, m, today, mine)}{agenda}</section>')
    later = [x for x in one_off if x["date"] > end]
    if later:
        out.append('<h2 id="later">Later</h2><ol class="agenda later">' + "".join(_agenda_item(x, today) for x in later) + "</ol>")
    rows = "".join(f'<li><strong>{e(r["title"])}</strong>: {e(cadence(item["cron"]))}. {e(r["owner"])}.</li>' for r, item in routines(cal, sched) if r["show"] != "note")
    key = "".join(f'<li class="t-{k}">{e(v)}</li>' for k, v in TYPES.items())
    out.append(f'<details><summary>Routines and how to read this</summary><ul>{rows}</ul>'
               f'<p>{"".join(e(r["title"]) + f": every day, around {run_time(sched)}. " for r in daily)}Times are Eastern. A \u2713 means done. '
               f'Routines show from {nice(d(cal["recurring_from"]))} on; earlier days show only what\'s on record.</p>'
               f'<p>Holiday themes follow a set lead time: plan 4 weeks out, design at 3, review at 2, Ryno\'s yes by 1. No yes, no switch.</p></details>'
               f'<p>Every routine and limit is on <a href="{up}schedule/">Schedule and limits</a>.</p>')
    return "".join(out)


def upcoming(cal, today):
    return sum(1 for x in dated(cal) if x["date"] > today)


# ---------- subscribe feed (RFC 5545): all-day events, CRLF lines folded at 75 octets, no personal data ----------
def _fold(line):
    b, out = line.encode(), []
    while len(b) > 75:
        cut = 75 if not out else 74
        while (b[cut] & 0xC0) == 0x80:  # never split a UTF-8 character
            cut -= 1
        out.append(b[:cut].decode())
        b = b[cut:]
    out.append(b.decode())
    return "\r\n ".join(out)


def _text(s):
    return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def rrule(expr):
    dom, mon, dow = parse_cron(expr)
    if mon is not None:
        return None
    if dom is None and dow is None:
        return "FREQ=DAILY"
    if dom is None and dow is not None:
        return "FREQ=WEEKLY;BYDAY=" + ",".join(ICS_DAY[x] for x in sorted(dow))
    if dom == set(range(1, 8)) and dow is not None and len(dow) == 1:
        return f"FREQ=MONTHLY;BYDAY=1{ICS_DAY[min(dow)]}"
    return None


def ics(cal, sched, today, base):
    stamp = today.strftime("%Y%m%dT120000Z")
    ymd = lambda x: x.strftime("%Y%m%d")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Slopworks//Team calendar//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "X-WR-CALNAME:Slopworks team calendar", "X-WR-TIMEZONE:America/New_York",
             "X-WR-CALDESC:" + _text(f"The Slopworks bot team's dated plans, reviews and holiday themes. The daily run is every day around {run_time(sched)}. Unofficial fan project.")]

    def event(uid, start, summary, desc, end=None, rule=None, tentative=False):
        lines.extend(["BEGIN:VEVENT", f"UID:{uid}.slopworks-calendar", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{ymd(start)}",
                      f"DTEND;VALUE=DATE:{ymd(end or start + timedelta(days=1))}"] + ([f"RRULE:{rule}"] if rule else [])
                     + [f"SUMMARY:{_text(summary)}", f"DESCRIPTION:{_text(desc)}", f"URL:{base}calendar/", "TRANSP:TRANSPARENT"]
                     + (["STATUS:TENTATIVE"] if tentative else ["STATUS:CONFIRMED"]) + ["END:VEVENT"])
    for x in dated(cal):
        event(x["id"], x["date"], x["title"], f'{TYPES[x["type"]]}. {who(x)}. {x["note"]}'.strip())
    for t in cal["themes"]:
        if t["status"] != "placeholder" and t.get("switch_on"):
            ok = yes_done(cal, t["id"])
            event(f'{t["id"]}-window', start_of(t), f'{t["name"]} blobs on the site', "Holiday character theme." + ("" if ok else " Only after Ryno's yes."),
                  end=d(t["switch_off"]) + timedelta(days=1), tentative=not ok)
    first = d(cal["recurring_from"])
    for r, item in routines(cal, sched):
        rule = rrule(item["cron"])
        if r["show"] == "note" or not rule:
            continue
        day = first
        while not matches(day, item["cron"]):
            day += timedelta(days=1)
        event(f'routine-{r["schedule_id"]}', day, r["title"], f'{TYPES[r["type"]]}. {r["owner"]}. {item["what"]}', rule=rule)
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"

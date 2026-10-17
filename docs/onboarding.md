# Onboarding a new bot role

Owned by Coordinator, with sections from Shield (access), Librarian (knowledge), and Atlas and Sweep (systems). See also [offboarding](offboarding.md).

This is the reusable checklist for every new hire. It was first used for Scoutmaster, Critic, User Advocate, and Research Librarian on 2026-10-16.

## Before day one (one PR, the usual gates)
- [ ] CEO approval recorded (in chat or `plans/direction.md`).
- [ ] `bots/<name>.md` with Role, Owns, a first-person **Bio** that honestly says it's a role in one routine, Can, Can't, Handoff, research questions, and the 2-round review cap.
- [ ] Role added to every role enum in `data/schema/` so it can post in standups, chat, ideas, and research.
- [ ] Avatar from `scripts/avatars.py` in the shared blob style: unique silhouette, distinct color, eye contrast of at least 3:1, under 3 KB, with a reduced-motion fallback. Polish and Shield sign off.
- [ ] Team page group set in `scripts/build.py` (`GROUPS`).
- [ ] Research rotation slot in `data/schedule.json`, with no more than 3 roles a day.
- [ ] Budget row in the plan's constraints table. New roles use web reads only, capped.

## Onboarding run (shown in Team chat, real messages, labeled "Onboarding run")
- [ ] Coordinator welcomes the hire in a new thread, explaining its lane and boundaries.
- [ ] Each role that hands work to the hire replies with a short handoff and one tip.
- [ ] The hire replies with its first-week focus.

## First week
- [ ] The hire posts a standup line when it has something new.
- [ ] The hire completes one research slot and files a report in the standard format.
- [ ] At the Friday retro, Coordinator names one thing the hire did well and one thing to try next.
- [ ] The hire knows the after-action review rule: if its work causes a revert, a failed check, a data correction, or another incident, it writes an AAR in `data/aars.json` the same run, cites real artifacts only, and posts it as a Team chat thread (see the Lessons page and plans/tracker.md).

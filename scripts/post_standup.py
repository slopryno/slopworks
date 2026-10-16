#!/usr/bin/env python3
"""Posts the latest standup to the read-only 'Team chat' Discussions category, then locks it.

Run from the box routine with the existing gh auth (no workflow token). Never runs in CI.
  post_standup.py            post today's standup if it's non-empty and not posted yet
  post_standup.py --dry-run  print what would be posted
Refuses to post if the body fails the personal-data or secret scan.
"""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check  # noqa: E402

OWNER, NAME, CATEGORY = "slopryno", "slopworks", "Team chat"


def body_for(lines):
    day = lines[0]["date"]
    rows = "\n".join(f"- **{l['role']}:** did {l['did']} · doing {l['doing']} · blockers: {l['blockers']}" for l in lines)
    return (f"Standup for {day}, generated from the run's data.\n\n{rows}\n\n"
            "Read-only: this thread is locked. Full Team chat, pitches, and the idea log: https://slopryno.github.io/slopworks/chat/\n\n"
            "Unofficial, fan-built project. Not affiliated with or endorsed by Grok Bot, SpaceX, or X.")


def gql(query, **vars):
    args = ["gh", "api", "graphql", "-f", f"query={query}"] + [x for k, v in vars.items() for x in ("-f", f"{k}={v}")]
    return json.loads(subprocess.run(args, check=True, capture_output=True, text=True).stdout)["data"]


def main():
    standup = json.loads((check.ROOT / "data/standup.json").read_text())
    if not standup:
        print("post_standup: no standup lines; nothing posted"); return
    day = max(l["date"] for l in standup)
    lines = [l for l in standup if l["date"] == day]
    title, body = f"Standup {day}", body_for(lines)
    if check.pii_hits(body) or check.secret_hits(body):
        sys.exit("post_standup: body failed the personal-data/secret scan; not posting")
    if "--dry-run" in sys.argv:
        print(title); print(body); return
    repo = gql("query($o:String!,$n:String!){repository(owner:$o,name:$n){id hasDiscussionsEnabled discussionCategories(first:25){nodes{id name}} discussions(first:20,orderBy:{field:CREATED_AT,direction:DESC}){nodes{title}}}}", o=OWNER, n=NAME)["repository"]
    if not repo["hasDiscussionsEnabled"]:
        sys.exit("post_standup: Discussions are off")
    cats = [c for c in repo["discussionCategories"]["nodes"] if c["name"] == CATEGORY]
    if not cats:
        sys.exit(f"post_standup: no '{CATEGORY}' category")
    if any(d["title"] == title for d in repo["discussions"]["nodes"]):
        print("post_standup: already posted"); return
    d = gql("mutation($r:ID!,$c:ID!,$t:String!,$b:String!){createDiscussion(input:{repositoryId:$r,categoryId:$c,title:$t,body:$b}){discussion{id url}}}",
            r=repo["id"], c=cats[0]["id"], t=title, b=body)["createDiscussion"]["discussion"]
    gql("mutation($id:ID!){lockLockable(input:{lockableId:$id,lockReason:RESOLVED}){lockedRecord{locked}}}", id=d["id"])
    print(f"post_standup: posted and locked {d['url']}")


if __name__ == "__main__":
    main()

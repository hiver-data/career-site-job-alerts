#!/usr/bin/env python3
"""Daily job alerts from company career sites via the hiver/career-site-job-search Apify Actor.

Reads config.yaml, runs the Actor with your APIFY_TOKEN, appends jobs not seen before
(dedupe by url) to jobs.csv, writes NEW_JOBS.md, and optionally posts them to Slack/Discord.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

import yaml

ACTOR = "hiver~career-site-job-search"
COLUMNS = ["first_seen", "company", "title", "location", "postedAt", "salary", "source", "url"]
DEFAULT_INPUT = {"maxJobs": 20, "includeDescription": False}


def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if not cfg.get("keywords"):
        sys.exit(f"{path}: 'keywords' is required (a list of words or phrases)")
    return {**DEFAULT_INPUT, **cfg}


def fetch_jobs(actor_input, token, api_base):
    url = f"{api_base}/v2/acts/{ACTOR}/run-sync-get-dataset-items?" + urllib.parse.urlencode({"token": token})
    req = urllib.request.Request(
        url, data=json.dumps(actor_input).encode(), method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=330) as resp:
        rows = json.load(resp)
    return [r for r in rows if isinstance(r, dict) and r.get("url")]


def salary_text(r):
    lo, hi = r.get("salaryMin"), r.get("salaryMax")
    if lo is None and hi is None:
        return ""
    cur, per = r.get("salaryCurrency") or "", r.get("salaryInterval") or ""
    rng = f"{lo:g}-{hi:g}" if lo is not None and hi is not None else f"{(lo if lo is not None else hi):g}"
    return " ".join(x for x in (rng, cur, "/" + per if per else "") if x)


def to_row(r, today):
    return {
        "first_seen": today, "company": r.get("company") or "", "title": r.get("title") or "",
        "location": r.get("location") or "", "postedAt": r.get("postedAt") or "",
        "salary": salary_text(r), "source": r.get("source") or "", "url": r["url"],
    }


def read_seen(path):
    if not os.path.exists(path):
        return set()
    with open(path, newline="", encoding="utf-8") as f:
        return {row["url"] for row in csv.DictReader(f)}


def append_csv(path, rows):
    new_file = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        if new_file:
            w.writeheader()
        w.writerows(rows)


def markdown(rows, today):
    if not rows:
        return f"# New jobs {today}\n\nNo new jobs.\n"
    out = [f"# New jobs {today}", "", f"{len(rows)} new job(s).", ""]
    for r in rows:
        meta = " | ".join(x for x in (r["location"], r["salary"], r["postedAt"][:10]) if x)
        out.append(f"- [{r['title']}]({r['url']}) - {r['company']}" + (f" ({meta})" if meta else ""))
    return "\n".join(out) + "\n"


def post_webhook(url, kind, rows):
    lines = [f"{r['title']} - {r['company']} ({r['location']}) {r['url']}" for r in rows[:15]]
    text = f"{len(rows)} new job(s)\n" + "\n".join(lines)
    body = {"text": text} if kind == "slack" else {"content": text[:1900]}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=30).read()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--csv", default="jobs.csv")
    p.add_argument("--md", default="NEW_JOBS.md")
    p.add_argument("--date", default=os.environ.get("ALERTS_DATE"), help="override today's date (YYYY-MM-DD), for tests")
    a = p.parse_args()

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("APIFY_TOKEN is not set (add it as a repository secret)")
    api_base = os.environ.get("APIFY_API_BASE", "https://api.apify.com").rstrip("/")
    today = a.date or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    jobs = fetch_jobs(load_config(a.config), token, api_base)
    seen = read_seen(a.csv)
    fresh, batch = [], set()
    for r in jobs:
        if r["url"] not in seen and r["url"] not in batch:
            batch.add(r["url"])
            fresh.append(to_row(r, today))
    fresh.sort(key=lambda x: (x["postedAt"], x["url"]), reverse=True)

    if fresh:
        append_csv(a.csv, fresh)
    with open(a.md, "w", encoding="utf-8", newline="\n") as f:
        f.write(markdown(fresh, today))

    for env, kind in (("SLACK_WEBHOOK_URL", "slack"), ("DISCORD_WEBHOOK_URL", "discord")):
        if fresh and os.environ.get(env):
            post_webhook(os.environ[env], kind, fresh)
    print(f"fetched {len(jobs)}, new {len(fresh)}, total tracked {len(seen) + len(fresh)}")


if __name__ == "__main__":
    main()

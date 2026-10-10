#!/usr/bin/env bash
# Offline test: no Apify account, no spend. Run from the repo root: bash tests/run_test.sh
set -euo pipefail
PORT=${PORT:-8765}
T=$(mktemp -d)
python3 tests/mock_apify.py "$PORT" tests/rows.json "$T/hooks.log" & MOCK=$!
trap 'kill $MOCK 2>/dev/null; rm -rf "$T"' EXIT
sleep 1
export APIFY_TOKEN=test APIFY_API_BASE="http://127.0.0.1:$PORT" ALERTS_DATE=2026-10-10
run() { python3 job_alerts.py --csv "$1/jobs.csv" --md "$1/NEW_JOBS.md"; }

mkdir "$T/a" "$T/b"
echo "== run 1 (empty state)"; run "$T/a"
echo "== run 2 (same state, mock now returns 3 jobs, 2 already seen)"
SLACK_WEBHOOK_URL="http://127.0.0.1:$PORT/hook" run "$T/a"
cp "$T/a/NEW_JOBS.md" "$T/second.md"

# determinism: replay run 1 against a fresh mock page order -> byte-identical files
kill $MOCK; python3 tests/mock_apify.py "$PORT" tests/rows.json "$T/hooks.log" & MOCK=$!; sleep 1
echo "== replay run 1 in a fresh dir"; run "$T/b"
python3 - "$T" <<'P'
import csv, hashlib, sys
t = sys.argv[1]
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:12]
# first-run outputs must match; compare run-1 CSV by re-deriving from fresh dir
a = list(csv.DictReader(open(f"{t}/a/jobs.csv")))
b = list(csv.DictReader(open(f"{t}/b/jobs.csv")))
assert len(a) == 4 and len(b) == 3, (len(a), len(b))
assert a[:3] == b, "first-run rows differ"
urls = [r["url"] for r in a]
assert len(urls) == len(set(urls)), "duplicate url in jobs.csv"
new = open(f"{t}/second.md").read()
assert "1 new job(s)" in new and "Series Procurement" in new and "Creative Advocate" not in new and "Performance Engineer" not in new
hooks = open(f"{t}/hooks.log").read()
assert hooks.count("\n") == 1 and "Series Procurement" in hooks and "Creative Advocate" not in hooks, "webhook should post only the new job"
print("OK: run-2 NEW_JOBS.md lists only the 1 unseen job; jobs.csv has 4 unique urls")
print("sha256 run1 CSV (a, first 3 rows) == fresh replay CSV (b):", h(f"{t}/b/jobs.csv"))
P
cmp <(head -4 "$T/a/jobs.csv") "$T/b/jobs.csv" && echo "OK: first-run CSV byte-identical on replay"
echo "== NEW_JOBS.md after run 2"; cat "$T/second.md"
echo "== jobs.csv"; cat "$T/a/jobs.csv"

# Career-site job alerts (GitHub Actions)

A daily job alert you own. A scheduled GitHub Actions workflow searches company career sites (Greenhouse, Lever, Ashby, Workday, SmartRecruiters and more) for your keywords with the [hiver/career-site-job-search](https://apify.com/hiver/career-site-job-search?utm_source=github&utm_campaign=job-alerts) Apify Actor, keeps only jobs it has not shown you before, and:

- appends them to `jobs.csv` (deduplicated by job `url`),
- writes `NEW_JOBS.md` with just today's new jobs,
- optionally posts them to Slack or Discord.

Pay ranges are read from the posting text when the career site does not expose them, so `jobs.csv` has a `salary` column where a posting states one.

## Setup (3 steps)

1. **Use this template**: fork or copy this repo into your own GitHub account.
2. **Add secrets** (Settings > Secrets and variables > Actions): `APIFY_TOKEN` (your own token from your Apify account). Optional: `SLACK_WEBHOOK_URL` and/or `DISCORD_WEBHOOK_URL`.
3. **Edit `config.yaml`** (keywords, `postedWithinDays`, optional locations) and run the `job-alerts` workflow once from the Actions tab. After that it runs daily at 06:17 UTC and commits new rows to `jobs.csv`.

`config.yaml` is passed straight to the Actor as its input. `maxJobs` defaults to 20 so each run stays small; you pay Apify for the Actor's usage on your own account.

## Test it offline (no Apify account)

```
pip install -r requirements.txt
bash tests/run_test.sh
```

The test starts a mock Apify API serving real rows from cloud runs of the Actor, runs the script twice, and checks that the second run emits only the job it has not seen, that no `url` repeats in `jobs.csv`, that a fresh replay of the first run gives a byte-identical CSV, and that the webhook gets only the new job.

## How the Actor compares

On the hiver Lab bench (build 0.6.7, 2026-10-09 20:52 UTC, 4 test cases across Greenhouse, Ashby, Workday and Personio boards), field accuracy against ground truth was 100% for `hiver/career-site-job-search`, 84% for `hirebase/job-search` and 58% for `fantastic-jobs/career-site-job-listing-api`. On the same bench, hirebase was slightly ahead on completeness (92% vs our 91%) and both competitors answered faster (about 2 s vs our 20 s). Store price in those runs was $7.05 per 1,000 jobs for `hiver/career-site-job-search`; hirebase's was lower. Four small cases is a small sample: check the output on your own keywords.

Actor page: https://apify.com/hiver/career-site-job-search?utm_source=github&utm_campaign=job-alerts

## Files

- `job_alerts.py`: the script (Python 3.9+, PyYAML only)
- `config.yaml`: your search
- `.github/workflows/job-alerts.yml`: the daily schedule
- `tests/`: mock Apify API, real sample rows, offline test

MIT licensed.

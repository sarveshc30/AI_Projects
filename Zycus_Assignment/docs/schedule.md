# Weekly Scheduler — Wiring Notes

(`python src/run_weekly.py --all`) that a scheduler just needs to invoke on a cadence.
`config/schedule.yaml` documents the intended cadence (weekly, Monday 07:00 IST).

## Option A — cron (any always-on Linux/WSL host)

```cron
# Runs every Monday at 07:00 server time, logs to a rotating file.
0 7 * * 1 cd /path/to/Zycus_Assignment && /path/to/conda/envs/LangGraph/bin/python src/run_weekly.py --all >> logs/weekly_run.log 2>&1
```

Add with `crontab -e`. Make sure `GROQ_API_KEY_1` (and `_2` as fallback) are available to the
cron environment — either export them in the crontab itself or ensure `.env` is readable from
the working directory `run_weekly.py` is invoked from (it loads `.env` via `python-dotenv`).

## Option B — GitHub Actions (no always-on host required)

```yaml
# .github/workflows/weekly-report.yml
name: Weekly Project Health Report
on:
  schedule:
    - cron: "30 1 * * 1"   # 07:00 IST Monday == 01:30 UTC Monday
  workflow_dispatch: {}      # allows manual triggering from the Actions tab

jobs:
  run-report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: python -c "import nltk; nltk.download('vader_lexicon')"
      - run: python src/run_weekly.py --all
        env:
          GROQ_API_KEY_1: ${{ secrets.GROQ_API_KEY_1 }}
          GROQ_API_KEY_2: ${{ secrets.GROQ_API_KEY_2 }}
      - uses: actions/upload-artifact@v4
        with:
          name: weekly-reports
          path: outputs/weekly/
```

Store the Groq keys as repository secrets (`Settings -> Secrets and variables -> Actions`).
The generated reports upload as a workflow artifact; wiring that into an email/Slack post is
a follow-up, not included here since it needs a destination the take-home doesn't specify.

## Why not more than this

The brief explicitly calls this a bonus and says "don't over-engineer standing infrastructure
for a demo" — this doc plus the two options above is enough for someone to wire it into
whatever their team already uses (cron box, GitHub Actions, Airflow DAG, etc.) without us
guessing at infra that isn't specified.

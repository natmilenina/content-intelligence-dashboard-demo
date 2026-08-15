# Content Intelligence Dashboard Demo

Sanitized, portfolio-ready Streamlit demo for investigating support-answer quality and knowledge gaps.

The first working version is intentionally small and BigQuery-backed from the start:

```text
synthetic support interactions
  -> BigQuery tables
  -> GoogleSQL views
  -> Python / Streamlit dashboard
```

No old production project, old Google Sheets, Telegram identifiers, private URLs, or service-account keys are used by the demo app.

## Current App

Run target:

```bash
streamlit run ton_content_dashboard_gh9082026_canonical.py
```

The app is read-only. It displays seeded synthetic review status, notes, assignees, and expert feedback from BigQuery.

## Setup

Follow the step-by-step runbook:

[docs/DEMO_RUNBOOK.md](docs/DEMO_RUNBOOK.md)

Short version:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export CONTENT_DEMO_GCP_PROJECT_ID="your-personal-project-id"
export CONTENT_DEMO_BQ_DATASET="content_intelligence_demo"
export CONTENT_DEMO_BQ_LOCATION="EU"

python scripts/setup_bigquery_demo.py \
  --project-id "$CONTENT_DEMO_GCP_PROJECT_ID" \
  --dataset-id "$CONTENT_DEMO_BQ_DATASET" \
  --location "$CONTENT_DEMO_BQ_LOCATION"

streamlit run ton_content_dashboard_gh9082026_canonical.py
```

You must authenticate to your own Google Cloud project with Application Default Credentials before running the setup script.

## BigQuery Assets

`sql/01_schema.sql`

- Creates `interactions`.
- Creates `expert_feedback`.

`sql/02_views.sql`

- Creates enriched interactions.
- Selects knowledge-gap candidates.
- Joins interactions to expert feedback.
- Builds the read-only review queue.
- Aggregates recurring problematic queries for early knowledge-gap insight.

## Synthetic Data

The generator creates a few hundred fictional support interactions and synthetic SME feedback records. The demo story covers:

- successful responses
- knowledge-not-found outcomes
- wrong and incomplete answers
- recurring unanswered questions
- multiple channels, audiences, languages, and topics
- seeded expert feedback and operational follow-up fields

The first demo keeps answer behavior and SME judgment separate: `response_outcome` lives on interactions, while `issue_type`, `review_category`, and `flagged_by` live in the expert feedback flow. Knowledge-not-found rows have no expert comments and no knowledge source ID.

## Deferred Work

The leading next iteration is semantic grouping of related unanswered queries into knowledge-gap themes for documentation prioritization.

Deferred deliberately:

- write-back workflow
- semantic clustering
- issue tracker integrations
- translation-service integrations
- production IAM/deployment architecture

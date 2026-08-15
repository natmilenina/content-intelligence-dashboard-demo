# Content Intelligence Dashboard

A sanitized Streamlit dashboard for reviewing synthetic support interactions, answer-quality issues, and recurring knowledge gaps.

The demo uses a real analytics flow:

```text
synthetic support data -> BigQuery -> GoogleSQL views -> Streamlit dashboard
```

## What It Shows

- support interactions with response outcomes
- expert feedback on selected assistant answers
- review queue for problematic answers
- knowledge-not-found cases
- recurring query patterns
- multilingual examples with optional English translations

All data is fictional and generated for the demo.

## Tech Stack

- Python
- Streamlit
- Google BigQuery
- GoogleSQL
- Pandas

## Run Locally

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your BigQuery configuration:

```bash
export CONTENT_DEMO_GCP_PROJECT_ID="your-gcp-project-id"
export CONTENT_DEMO_BQ_DATASET="content_intelligence_demo"
export CONTENT_DEMO_BQ_LOCATION="EU"
```

Create and load the demo BigQuery tables/views:

```bash
python scripts/setup_bigquery_demo.py \
  --project-id "$CONTENT_DEMO_GCP_PROJECT_ID" \
  --dataset-id "$CONTENT_DEMO_BQ_DATASET" \
  --location "$CONTENT_DEMO_BQ_LOCATION"
```

Run the dashboard:

```bash
streamlit run app.py
```

## BigQuery Objects

- `interactions`: synthetic support conversations
- `expert_feedback`: synthetic expert review records
- `vw_interactions_enriched`: normalized dashboard-ready interactions
- `vw_review_items`: review queue joining interactions and expert feedback
- `vw_knowledge_gap_candidates`: unanswered support requests
- `vw_recurring_query_summary`: repeated issue patterns

## Notes

The public demo is read-only. It does not use production data, old infrastructure, Google Sheets, Telegram integrations, or service-account key files.

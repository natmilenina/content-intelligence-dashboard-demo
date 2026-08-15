# BigQuery-Backed Demo Runbook

This runbook sets up the first sanitized portfolio demo. It uses synthetic data only.

## What You Create In Google Cloud

You create only the minimum resources required for the MVP:

- One personal Google Cloud project that you control.
- BigQuery API enabled in that project.
- One BigQuery dataset, default name: `content_intelligence_demo`.
- Two tables: `interactions`, `expert_feedback`.
- Five views:
  - `vw_interactions_enriched`
  - `vw_knowledge_gap_candidates`
  - `vw_interaction_feedback`
  - `vw_review_items`
  - `vw_recurring_query_summary`

No old production project, old Sheets, old Telegram identifiers, or old service-account keys are used.

## User Actions In Your Personal Google Cloud Project

1. Create or choose a personal Google Cloud project.
2. Enable the BigQuery API.
3. Authenticate locally with Google Application Default Credentials.

If you use the Google Cloud SDK, the local authentication command is:

```bash
gcloud auth application-default login
```

This command is for you to run. Codex did not run it.

## Repository Actions

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set your personal demo configuration:

```bash
export CONTENT_DEMO_GCP_PROJECT_ID="your-personal-project-id"
export CONTENT_DEMO_BQ_DATASET="content_intelligence_demo"
export CONTENT_DEMO_BQ_LOCATION="EU"
```

Create the dataset, generate synthetic data, load the two tables, and create the views:

```bash
python scripts/setup_bigquery_demo.py \
  --project-id "$CONTENT_DEMO_GCP_PROJECT_ID" \
  --dataset-id "$CONTENT_DEMO_BQ_DATASET" \
  --location "$CONTENT_DEMO_BQ_LOCATION"
```

Rerunning this setup command refreshes the demo in place. The schema file drops the synthetic demo views and tables, recreates the current schema, and the load jobs use `WRITE_TRUNCATE`. Existing demo data is replaced rather than duplicated.

Start Streamlit:

```bash
streamlit run ton_content_dashboard_gh9082026_canonical.py
```

## SQL Files

`sql/01_schema.sql`

- Creates the `interactions` table.
- Creates the `expert_feedback` table.
- Partitions both tables by date.
- Clusters on fields commonly used by the dashboard filters.

`sql/02_views.sql`

- `vw_interactions_enriched`: normalizes interaction records and derives `normalized_query`, `assistant_answered`, and `is_knowledge_gap`.
- `vw_knowledge_gap_candidates`: selects interactions where the assistant could not find a matching knowledge source.
- `vw_interaction_feedback`: joins interactions to expert feedback.
- `vw_review_items`: creates the read-only review queue consumed by Streamlit. Knowledge gaps come from `response_outcome`; answer-quality issues come from expert feedback.
- `vw_recurring_query_summary`: aggregates repeated problematic queries for early knowledge-gap insight.

## Synthetic Data

The generator creates about 360 interactions and 85 expert feedback records by default.

The fictional product/support domain is unrelated to the original production data. Storylines include:

- Plan limits after a pricing update.
- API retry-after handling.
- Invoice export timing.
- Passwordless mobile login recovery.
- Return exception policy.
- Partner sandbox access.

The generated rows include successful answers, knowledge-not-found outcomes, wrong or incomplete answers, recurring questions, multiple channels, multiple requester types, multiple languages, synthetic knowledge-source references, synthetic expert notes, and seeded review statuses.

The data model intentionally keeps interaction behavior separate from SME review:

- `interactions.response_outcome` describes what the assistant did. The first demo uses `answered` and `knowledge_not_found`.
- `interactions` does not contain `issue_type` or `probable_cause`.
- `expert_feedback.issue_type` is populated only for answered interactions that an expert reviewed.
- Knowledge-not-found interactions do not receive expert comments in the synthetic feedback table.
- `review_category` is derived for the dashboard: `Knowledge gap` for no-answer rows, `Answer quality` for wrong/incomplete/unrelated answered rows, and `Presentation cleanup` for a small sample of correct answers with minor formatting or repetition issues.
- `knowledge_source_id` is blank only when `response_outcome = knowledge_not_found`.
- `knowledge_snippet` uses `No matching knowledge source was retrieved for this synthetic interaction.` only when `response_outcome = knowledge_not_found`.
- `flagged_by` uses fictional values such as `Expert 1` through `Expert 4` and appears only on expert-feedback rows.
- Non-English rows use localized synthetic user requests and localized synthetic assistant answers. The English query and English assistant answer are stored in `query_translation` and `response_translation`.
- The dashboard hides translation columns by default. Use `Show English translations` in the Review Queue or All Conversations table to display both translation columns.

### BigQuery Sandbox retention

The initial portfolio demo runs on BigQuery Sandbox so that development can proceed without attaching a billing account. During validation, the synthetic generator initially produced 360 interactions across approximately 90 days, but only 246 were retained in BigQuery. The earliest retained row exactly matched the 60-day cutoff, confirming that older date partitions were being expired by the Sandbox environment.

The synthetic data window was therefore reduced to 45 days. This keeps the complete demo dataset inside the Sandbox retention period while preserving enough temporal variation for trends and recurring-issue analysis.

This is an environment constraint rather than application business logic. A production or billed deployment could use a longer analytical history with explicit dataset/table retention policies.

The demo is designed to be cheaply recreated by rerunning the setup script rather than relying on permanent Sandbox storage. Future-dating synthetic interactions is intentionally not used as a retention workaround because it would distort recency and trend behavior, and it would not guarantee persistence of Sandbox resources.

For reproducible local demos or tests, anchor generation to a specific UTC date:

```bash
python scripts/generate_synthetic_data.py --reference-date 2026-08-09
```

The full BigQuery setup script accepts the same option:

```bash
python scripts/setup_bigquery_demo.py \
  --project-id "$CONTENT_DEMO_GCP_PROJECT_ID" \
  --dataset-id "$CONTENT_DEMO_BQ_DATASET" \
  --location "$CONTENT_DEMO_BQ_LOCATION" \
  --reference-date 2026-08-09
```

## Read-Only Behavior

The public MVP is read-only. It displays review status, assignee, notes, and expert feedback as seeded synthetic data from BigQuery. It does not write to BigQuery or Google Sheets.

## Deferred Features

- Semantic clustering of related knowledge gaps.
- Production-grade write-back or review action history.
- External issue tracker integrations.
- Translation APIs.
- Complex IAM or deployment architecture.

The recommended next iteration is semantic knowledge-gap clustering over unanswered and problematic queries.

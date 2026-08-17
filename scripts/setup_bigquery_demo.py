"""Create and load the sanitized BigQuery demo dataset using ADC."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Dict, Iterable

from google.cloud import bigquery

from generate_synthetic_data import generate_files


ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"


INTERACTION_SCHEMA = [
    bigquery.SchemaField("interaction_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("conversation_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("message_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("timestamp_utc", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("request_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("channel_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("channel_name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("audience_type", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("conversation_ref", "STRING"),
    bigquery.SchemaField("language", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("user_request", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("query_translation", "STRING"),
    bigquery.SchemaField("bot_response", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("response_translation", "STRING"),
    bigquery.SchemaField("response_outcome", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("topic", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("confidence_score", "FLOAT"),
    bigquery.SchemaField("response_latency_ms", "INTEGER"),
    bigquery.SchemaField("knowledge_source_id", "STRING"),
    bigquery.SchemaField("knowledge_snippet", "STRING"),
    bigquery.SchemaField("fallback_pattern", "STRING"),
    bigquery.SchemaField("synthetic_storyline_id", "STRING", mode="REQUIRED"),
]

FEEDBACK_SCHEMA = [
    bigquery.SchemaField("feedback_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("interaction_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("conversation_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("feedback_timestamp", "TIMESTAMP", mode="REQUIRED"),
    bigquery.SchemaField("feedback_date", "DATE", mode="REQUIRED"),
    bigquery.SchemaField("flagged_by", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("issue_type", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("review_category", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("priority", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("feedback_outcome", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("suggested_answer", "STRING"),
    bigquery.SchemaField("notes", "STRING"),
    bigquery.SchemaField("resolution_status", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("assigned_to", "STRING", mode="REQUIRED"),
]


def render_sql(path: Path, project_id: str, dataset_id: str) -> str:
    return path.read_text(encoding="utf-8").format(project_id=project_id, dataset_id=dataset_id)


def run_sql_files(client: bigquery.Client, paths: Iterable[Path], project_id: str, dataset_id: str, location: str):
    for path in paths:
        query = render_sql(path, project_id, dataset_id)
        print(f"Running {path.relative_to(ROOT)}")
        client.query(query, location=location).result()


def create_dataset(client: bigquery.Client, project_id: str, dataset_id: str, location: str):
    dataset = bigquery.Dataset(f"{project_id}.{dataset_id}")
    dataset.location = location
    client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset ready: {project_id}.{dataset_id}")


def load_csv(client: bigquery.Client, table_id: str, csv_path: Path, schema):
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )
    with csv_path.open("rb") as handle:
        job = client.load_table_from_file(handle, table_id, job_config=job_config)
    job.result()
    table = client.get_table(table_id)
    print(f"Loaded {table.num_rows} rows into {table_id}")


def main():
    parser = argparse.ArgumentParser(description="Set up the BigQuery-backed synthetic demo.")
    parser.add_argument("--project-id", default=os.environ.get("CONTENT_DEMO_GCP_PROJECT_ID"), required=False)
    parser.add_argument("--dataset-id", default=os.environ.get("CONTENT_DEMO_BQ_DATASET", "content_intelligence_demo"))
    parser.add_argument("--location", default=os.environ.get("CONTENT_DEMO_BQ_LOCATION", "EU"))
    parser.add_argument("--output-dir", default="data/synthetic")
    parser.add_argument("--interactions", type=int, default=360)
    parser.add_argument("--seed", type=int, default=20260809)
    parser.add_argument(
        "--reference-date",
        help="Optional UTC anchor date or ISO datetime for reproducible 45-day synthetic windows.",
    )
    args = parser.parse_args()

    if not args.project_id:
        raise SystemExit("Provide --project-id or CONTENT_DEMO_GCP_PROJECT_ID.")

    client = bigquery.Client(project=args.project_id, location=args.location)
    create_dataset(client, args.project_id, args.dataset_id, args.location)

    run_sql_files(client, [SQL_DIR / "01_schema.sql"], args.project_id, args.dataset_id, args.location)
    paths: Dict[str, Path] = generate_files(Path(args.output_dir), args.interactions, args.seed, args.reference_date)

    load_csv(
        client,
        f"{args.project_id}.{args.dataset_id}.interactions",
        paths["interactions"],
        INTERACTION_SCHEMA,
    )
    load_csv(
        client,
        f"{args.project_id}.{args.dataset_id}.expert_feedback",
        paths["expert_feedback"],
        FEEDBACK_SCHEMA,
    )
    run_sql_files(client, [SQL_DIR / "02_views.sql"], args.project_id, args.dataset_id, args.location)

    print("BigQuery demo setup complete.")
    print(f"Set CONTENT_DEMO_GCP_PROJECT_ID={args.project_id}")
    print(f"Set CONTENT_DEMO_BQ_DATASET={args.dataset_id}")
    print("Run: streamlit run app.py")


if __name__ == "__main__":
    main()

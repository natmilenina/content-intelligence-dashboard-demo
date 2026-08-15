-- BigQuery schema for the sanitized Content Intelligence Dashboard demo.
-- Placeholders are filled by scripts/setup_bigquery_demo.py:
--   {project_id}
--   {dataset_id}

-- Drop demo views first because they depend on the tables below.
-- This setup script is intentionally destructive for the synthetic demo dataset:
-- rerunning it recreates the demo from generated synthetic data.
DROP VIEW IF EXISTS `{project_id}.{dataset_id}.vw_recurring_query_summary`;
DROP VIEW IF EXISTS `{project_id}.{dataset_id}.vw_review_items`;
DROP VIEW IF EXISTS `{project_id}.{dataset_id}.vw_interaction_feedback`;
DROP VIEW IF EXISTS `{project_id}.{dataset_id}.vw_knowledge_gap_candidates`;
DROP VIEW IF EXISTS `{project_id}.{dataset_id}.vw_interactions_enriched`;

DROP TABLE IF EXISTS `{project_id}.{dataset_id}.expert_feedback`;
DROP TABLE IF EXISTS `{project_id}.{dataset_id}.interactions`;

CREATE TABLE `{project_id}.{dataset_id}.interactions` (
  interaction_id STRING NOT NULL,
  conversation_id STRING NOT NULL,
  message_id STRING NOT NULL,
  timestamp_utc TIMESTAMP NOT NULL,
  request_date DATE NOT NULL,
  channel_id STRING NOT NULL,
  channel_name STRING NOT NULL,
  audience_type STRING NOT NULL,
  conversation_ref STRING,
  language STRING NOT NULL,
  user_request STRING NOT NULL,
  query_translation STRING,
  bot_response STRING NOT NULL,
  response_translation STRING,
  response_outcome STRING NOT NULL,
  topic STRING NOT NULL,
  confidence_score FLOAT64,
  response_latency_ms INT64,
  knowledge_source_id STRING,
  knowledge_snippet STRING,
  fallback_pattern STRING,
  synthetic_storyline_id STRING NOT NULL
)
PARTITION BY request_date
CLUSTER BY response_outcome, language, audience_type, topic;

CREATE TABLE `{project_id}.{dataset_id}.expert_feedback` (
  feedback_id STRING NOT NULL,
  interaction_id STRING NOT NULL,
  conversation_id STRING NOT NULL,
  feedback_timestamp TIMESTAMP NOT NULL,
  feedback_date DATE NOT NULL,
  flagged_by STRING NOT NULL,
  issue_type STRING NOT NULL,
  review_category STRING NOT NULL,
  priority STRING NOT NULL,
  feedback_outcome STRING NOT NULL,
  suggested_answer STRING,
  notes STRING,
  resolution_status STRING NOT NULL,
  assigned_to STRING NOT NULL
)
PARTITION BY feedback_date
CLUSTER BY issue_type, review_category, priority, resolution_status;

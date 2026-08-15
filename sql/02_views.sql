-- GoogleSQL views for the sanitized Content Intelligence Dashboard demo.
-- These views keep meaningful analytics logic in BigQuery instead of treating
-- BigQuery as passive file storage.

CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.vw_interactions_enriched` AS
SELECT
  interaction_id,
  conversation_id,
  message_id,
  timestamp_utc,
  request_date,
  channel_id,
  channel_name,
  audience_type,
  conversation_ref,
  language,
  user_request,
  query_translation,
  bot_response,
  response_translation,
  response_outcome,
  topic,
  confidence_score,
  response_latency_ms,
  knowledge_source_id,
  knowledge_snippet,
  fallback_pattern,
  synthetic_storyline_id,
  LOWER(TRIM(REGEXP_REPLACE(user_request, r'[^A-Za-z0-9]+', ' '))) AS normalized_query,
  response_outcome = 'answered' AS assistant_answered,
  response_outcome = 'knowledge_not_found' AS is_knowledge_gap
FROM `{project_id}.{dataset_id}.interactions`;

CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.vw_knowledge_gap_candidates` AS
SELECT *
FROM `{project_id}.{dataset_id}.vw_interactions_enriched`
WHERE response_outcome = 'knowledge_not_found';

CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.vw_interaction_feedback` AS
SELECT
  i.*,
  f.feedback_id,
  f.feedback_timestamp,
  f.flagged_by,
  f.issue_type AS feedback_issue_type,
  f.review_category AS feedback_review_category,
  f.priority AS feedback_priority,
  f.feedback_outcome,
  f.suggested_answer,
  f.notes AS feedback_notes,
  f.resolution_status AS feedback_resolution_status,
  f.assigned_to AS feedback_assigned_to
FROM `{project_id}.{dataset_id}.vw_interactions_enriched` AS i
LEFT JOIN `{project_id}.{dataset_id}.expert_feedback` AS f
USING (interaction_id, conversation_id);

CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.vw_review_items` AS
SELECT
  timestamp_utc,
  request_date,
  channel_name,
  channel_id,
  audience_type,
  conversation_ref,
  message_id,
  conversation_id,
  user_request,
  query_translation,
  language,
  bot_response,
  response_translation,
  response_outcome,
  CASE
    WHEN response_outcome = 'knowledge_not_found' THEN 'Knowledge gap'
    ELSE feedback_review_category
  END AS review_category,
  feedback_issue_type AS issue_type,
  COALESCE(
    feedback_priority,
    CASE
      WHEN response_outcome = 'knowledge_not_found' THEN 'High'
      ELSE 'Low'
    END
  ) AS priority,
  COALESCE(feedback_resolution_status, 'New') AS resolution_status,
  COALESCE(feedback_assigned_to, 'Docs Team') AS assigned_to,
  CASE
    WHEN feedback_issue_type IS NOT NULL THEN feedback_notes
    ELSE NULL
  END AS notes,
  CASE
    WHEN feedback_issue_type IS NOT NULL THEN flagged_by
    ELSE NULL
  END AS flagged_by,
  topic,
  knowledge_source_id,
  knowledge_snippet,
  synthetic_storyline_id,
  feedback_id,
  feedback_outcome,
  suggested_answer
FROM `{project_id}.{dataset_id}.vw_interaction_feedback`
WHERE response_outcome = 'knowledge_not_found' OR feedback_id IS NOT NULL;

CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.vw_recurring_query_summary` AS
SELECT
  topic,
  normalized_query,
  ARRAY_AGG(user_request ORDER BY timestamp_utc DESC LIMIT 1)[OFFSET(0)] AS example_query,
  COUNT(*) AS total_interactions,
  COUNTIF(response_outcome = 'knowledge_not_found' OR feedback_id IS NOT NULL) AS review_signals,
  COUNTIF(response_outcome = 'knowledge_not_found') AS knowledge_gap_interactions,
  COUNTIF(feedback_id IS NOT NULL) AS expert_feedback_count,
  COUNTIF(feedback_issue_type IN ('Wrong answer', 'Incomplete answer', 'Unrelated answer'))
    AS answer_quality_issues,
  STRING_AGG(DISTINCT language, ', ' ORDER BY language LIMIT 6) AS languages,
  STRING_AGG(DISTINCT channel_name, ', ' ORDER BY channel_name LIMIT 6) AS channels,
  MAX(request_date) AS latest_seen
FROM `{project_id}.{dataset_id}.vw_interaction_feedback`
GROUP BY topic, normalized_query
HAVING total_interactions >= 2 OR review_signals >= 1
ORDER BY knowledge_gap_interactions DESC, answer_quality_issues DESC, review_signals DESC, total_interactions DESC;

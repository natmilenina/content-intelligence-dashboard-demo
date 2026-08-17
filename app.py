"""
Sanitized Content Intelligence Dashboard demo.

This is the portfolio project derived from the canonical working dashboard.
It is intentionally read-only and BigQuery-backed from the start:

synthetic support interactions -> BigQuery tables/views -> GoogleSQL -> Streamlit
"""

from __future__ import annotations

import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account


st.set_page_config(
    page_title="Content Intelligence Dashboard",
    page_icon="CI",
    layout="wide",
    initial_sidebar_state="expanded",
)


PRIORITIES = ["High", "Medium", "Low"]
STATUSES = ["New", "In Progress", "Resolved", "Won't Fix"]

REVIEW_CATEGORY_COLORS = {
    "Knowledge gap": "#7c3aed",
    "Answer quality": "#dc2626",
    "Presentation cleanup": "#16a34a",
}

CONFIG_HELP = """
Set these values in your shell or Streamlit secrets:

- CONTENT_DEMO_GCP_PROJECT_ID
- CONTENT_DEMO_BQ_DATASET

Optional overrides:

- CONTENT_DEMO_BQ_LOCATION
- CONTENT_DEMO_REVIEW_VIEW
- CONTENT_DEMO_CONVERSATIONS_VIEW
- CONTENT_DEMO_RECURRING_VIEW
- CONTENT_DEMO_MAX_BYTES_BILLED
"""


@dataclass(frozen=True)
class DemoConfig:
    project_id: str
    dataset_id: str
    location: str
    review_view: str
    conversations_view: str
    recurring_view: str
    max_bytes_billed: int


def _setting(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value not in (None, ""):
        return value

    try:
        if name in st.secrets:
            secret_value = st.secrets.get(name)
            if secret_value not in (None, ""):
                return str(secret_value)
    except Exception:
        # Local development can use environment variables only; no secrets.toml is required.
        pass

    return default


def _secret_section(name: str) -> Optional[Dict[str, str]]:
    try:
        if name in st.secrets:
            return dict(st.secrets.get(name))
    except Exception:
        # Local development can use Application Default Credentials only.
        pass

    return None


def load_config() -> DemoConfig:
    project_id = _setting("CONTENT_DEMO_GCP_PROJECT_ID")
    dataset_id = _setting("CONTENT_DEMO_BQ_DATASET", "content_intelligence_demo")
    if not project_id:
        st.error("Missing BigQuery project configuration.")
        st.code(CONFIG_HELP, language="text")
        st.stop()

    return DemoConfig(
        project_id=project_id,
        dataset_id=dataset_id or "content_intelligence_demo",
        location=_setting("CONTENT_DEMO_BQ_LOCATION", "EU") or "EU",
        review_view=_setting("CONTENT_DEMO_REVIEW_VIEW", "vw_review_items") or "vw_review_items",
        conversations_view=_setting("CONTENT_DEMO_CONVERSATIONS_VIEW", "vw_interactions_enriched")
        or "vw_interactions_enriched",
        recurring_view=_setting("CONTENT_DEMO_RECURRING_VIEW", "vw_recurring_query_summary")
        or "vw_recurring_query_summary",
        max_bytes_billed=int(_setting("CONTENT_DEMO_MAX_BYTES_BILLED", "100000000") or "100000000"),
    )


def _validate_identifier(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"{label} must be a BigQuery identifier, got {value!r}")
    return value


def table_ref(config: DemoConfig, object_name: str) -> str:
    dataset = _validate_identifier(config.dataset_id, "dataset_id")
    name = _validate_identifier(object_name, "table_or_view_name")
    return f"`{config.project_id}.{dataset}.{name}`"


@st.cache_resource
def get_bigquery_client(project_id: str, location: str) -> bigquery.Client:
    service_account_info = _secret_section("gcp_service_account")
    if service_account_info:
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        return bigquery.Client(project=project_id, credentials=credentials, location=location)

    # Local fallback: uses Google Application Default Credentials.
    return bigquery.Client(project=project_id, location=location)


def run_query(
    client: bigquery.Client,
    config: DemoConfig,
    query: str,
    parameters: Optional[List[bigquery.ScalarQueryParameter]] = None,
) -> pd.DataFrame:
    job_config = bigquery.QueryJobConfig(
        query_parameters=parameters or [],
        maximum_bytes_billed=config.max_bytes_billed,
        use_query_cache=True,
    )
    return client.query(query, job_config=job_config, location=config.location).to_dataframe()


@st.cache_data(ttl=900)
def get_available_date_range(project_id: str, dataset_id: str, location: str, conversations_view: str, max_bytes: int):
    config = DemoConfig(project_id, dataset_id, location, "vw_review_items", conversations_view, "vw_recurring_query_summary", max_bytes)
    client = get_bigquery_client(project_id, location)
    query = f"""
        SELECT
          MIN(DATE(timestamp_utc)) AS min_date,
          MAX(DATE(timestamp_utc)) AS max_date
        FROM {table_ref(config, conversations_view)}
    """
    df = run_query(client, config, query)
    if df.empty or pd.isna(df.loc[0, "min_date"]) or pd.isna(df.loc[0, "max_date"]):
        today = date.today()
        return today - timedelta(days=90), today
    return pd.to_datetime(df.loc[0, "min_date"]).date(), pd.to_datetime(df.loc[0, "max_date"]).date()


@st.cache_data(ttl=900)
def load_review_items(
    project_id: str,
    dataset_id: str,
    location: str,
    review_view: str,
    max_bytes: int,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    config = DemoConfig(project_id, dataset_id, location, review_view, "vw_interactions_enriched", "vw_recurring_query_summary", max_bytes)
    client = get_bigquery_client(project_id, location)
    query = f"""
        SELECT
          timestamp_utc,
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
          review_category,
          issue_type,
          priority,
          resolution_status,
          assigned_to,
          notes,
          flagged_by,
          topic,
          knowledge_source_id,
          knowledge_snippet,
          synthetic_storyline_id,
          feedback_id,
          feedback_outcome,
          suggested_answer
        FROM {table_ref(config, review_view)}
        WHERE DATE(timestamp_utc) BETWEEN @start_date AND @end_date
        ORDER BY timestamp_utc DESC
        LIMIT 1000
    """
    return run_query(
        client,
        config,
        query,
        [
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date.isoformat()),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date.isoformat()),
        ],
    )


@st.cache_data(ttl=900)
def load_all_conversations(
    project_id: str,
    dataset_id: str,
    location: str,
    conversations_view: str,
    max_bytes: int,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    config = DemoConfig(project_id, dataset_id, location, "vw_review_items", conversations_view, "vw_recurring_query_summary", max_bytes)
    client = get_bigquery_client(project_id, location)
    query = f"""
        SELECT
          timestamp_utc,
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
          topic,
          knowledge_source_id,
          knowledge_snippet,
          synthetic_storyline_id
        FROM {table_ref(config, conversations_view)}
        WHERE DATE(timestamp_utc) BETWEEN @start_date AND @end_date
        ORDER BY timestamp_utc DESC
        LIMIT 1000
    """
    return run_query(
        client,
        config,
        query,
        [
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date.isoformat()),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date.isoformat()),
        ],
    )


@st.cache_data(ttl=900)
def load_recurring_summary(
    project_id: str,
    dataset_id: str,
    location: str,
    recurring_view: str,
    max_bytes: int,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    config = DemoConfig(project_id, dataset_id, location, "vw_review_items", "vw_interactions_enriched", recurring_view, max_bytes)
    client = get_bigquery_client(project_id, location)
    query = f"""
        SELECT
          topic,
          normalized_query,
          example_query,
          total_interactions,
          review_signals,
          knowledge_gap_interactions,
          expert_feedback_count,
          answer_quality_issues,
          languages,
          channels,
          latest_seen
        FROM {table_ref(config, recurring_view)}
        WHERE latest_seen BETWEEN @start_date AND @end_date
        ORDER BY knowledge_gap_interactions DESC, answer_quality_issues DESC, review_signals DESC, total_interactions DESC
        LIMIT 50
    """
    return run_query(
        client,
        config,
        query,
        [
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date.isoformat()),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date.isoformat()),
        ],
    )


def render_sidebar_filters(df: pd.DataFrame, all_conversations_df: pd.DataFrame) -> Dict:
    st.sidebar.header("Filters")
    filters: Dict = {}

    def options_from(column: str, frames: List[pd.DataFrame]) -> List[str]:
        values = set()
        for frame in frames:
            if column in frame.columns:
                values.update(v for v in frame[column].dropna().astype(str).unique() if v)
        return ["All"] + sorted(values)

    if "timestamp_utc" in df.columns and not df.empty:
        valid_dates = pd.to_datetime(df["timestamp_utc"], errors="coerce").dropna()
        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            selected = st.sidebar.date_input(
                "Date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )
            if isinstance(selected, tuple) and len(selected) == 2:
                filters["date_range"] = selected

    filters["audience_type"] = st.sidebar.multiselect(
        "Requester type",
        options=options_from("audience_type", [df, all_conversations_df]),
        default=["All"],
    )
    filters["channel"] = st.sidebar.multiselect(
        "Channel",
        options=options_from("channel_name", [df, all_conversations_df]),
        default=["All"],
    )
    filters["review_category"] = st.sidebar.multiselect(
        "Review category",
        options=options_from("review_category", [df]),
        default=["All"],
    )
    filters["issue_type"] = st.sidebar.multiselect(
        "Issue type",
        options=options_from("issue_type", [df]),
        default=["All"],
    )
    filters["response_outcome"] = st.sidebar.multiselect(
        "Response outcome",
        options=options_from("response_outcome", [df, all_conversations_df]),
        default=["All"],
    )
    filters["priority"] = st.sidebar.multiselect("Priority", options=["All"] + PRIORITIES, default=["All"])
    filters["status"] = st.sidebar.multiselect("Review status", options=["All"] + STATUSES, default=["All"])
    filters["assigned_to"] = st.sidebar.multiselect(
        "Assigned to",
        options=options_from("assigned_to", [df]),
        default=["All"],
    )
    filters["language"] = st.sidebar.multiselect(
        "Language",
        options=options_from("language", [df, all_conversations_df]),
        default=["All"],
    )
    filters["topic"] = st.sidebar.multiselect(
        "Topic",
        options=options_from("topic", [df, all_conversations_df]),
        default=["All"],
    )
    return filters


def apply_filters(df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
    filtered = df.copy()
    if filtered.empty:
        return filtered

    if "timestamp_utc" in filtered.columns:
        filtered["timestamp_utc"] = pd.to_datetime(filtered["timestamp_utc"], errors="coerce")

    if "date_range" in filters and "timestamp_utc" in filtered.columns:
        start_date, end_date = filters["date_range"]
        filtered = filtered[
            (filtered["timestamp_utc"].dt.date >= start_date)
            & (filtered["timestamp_utc"].dt.date <= end_date)
        ]

    mapping = {
        "audience_type": "audience_type",
        "channel": "channel_name",
        "review_category": "review_category",
        "issue_type": "issue_type",
        "response_outcome": "response_outcome",
        "priority": "priority",
        "status": "resolution_status",
        "assigned_to": "assigned_to",
        "language": "language",
        "topic": "topic",
    }
    for filter_name, column in mapping.items():
        selected = filters.get(filter_name, ["All"])
        if column in filtered.columns and "All" not in selected:
            filtered = filtered[filtered[column].astype(str).isin(selected)]
    return filtered

def render_demo_guide():
    st.info(
        """
        **How to read this demo**

        This demo shows how scattered AI support signals can be turned into a review & triage workflow.

        It combines synthetic support conversations, expert feedback, knowledge gaps, and recurring issue patterns so a team can decide whether a failure needs a content update, prompt change, routing fix, escalation rule, or product follow-up.
        """
    )

def render_summary_metrics(df: pd.DataFrame):
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Review items", len(df))
    with col2:
        value = len(df[df["resolution_status"] == "New"]) if "resolution_status" in df.columns else 0
        st.metric("New", value)
    with col3:
        value = len(df[df["priority"] == "High"]) if "priority" in df.columns else 0
        st.metric("High priority", value)
    with col4:
        if "review_category" in df.columns:
            value = len(df[df["review_category"] == "Knowledge gap"])
        elif "response_outcome" in df.columns:
            value = len(df[df["response_outcome"] == "knowledge_not_found"])
        else:
            value = 0
        st.metric("Knowledge gaps", value)
    with col5:
        value = df["topic"].nunique() if "topic" in df.columns else 0
        st.metric("Topics", value)


def render_review_table(df: pd.DataFrame):
    st.subheader("Review Queue")
    st.caption("Read-only demo view. Review status and notes are synthetic seeded fields.")
    if df.empty:
        st.info("No review items match the current filters.")
        return

    show_translations = st.checkbox("Show English translations", value=False, key="review_show_translations")
    display_columns = [
        "timestamp_utc",
        "channel_name",
        "audience_type",
        "conversation_ref",
        "user_request",
    ]
    if show_translations:
        display_columns.append("query_translation")
    display_columns.append("bot_response")
    if show_translations:
        display_columns.append("response_translation")
    display_columns.extend(
        [
            "response_outcome",
            "review_category",
            "issue_type",
            "priority",
            "resolution_status",
            "assigned_to",
            "flagged_by",
            "notes",
            "language",
            "topic",
            "knowledge_source_id",
            "knowledge_snippet",
            "suggested_answer",
        ]
    )
    display_columns = [col for col in display_columns if col in df.columns]
    table = df[display_columns].copy()
    if "timestamp_utc" in table.columns:
        table["timestamp_utc"] = pd.to_datetime(table["timestamp_utc"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp_utc": st.column_config.TextColumn("Timestamp", width="medium"),
            "channel_name": st.column_config.TextColumn("Channel", width="medium"),
            "audience_type": st.column_config.TextColumn("Requester type", width="medium"),
            "conversation_ref": st.column_config.TextColumn(
                "Synthetic conversation",
                width="medium",
            ),
            "user_request": st.column_config.TextColumn("User request", width="large"),
            "query_translation": st.column_config.TextColumn("User request (EN)", width="large"),
            "bot_response": st.column_config.TextColumn("Assistant answer", width="large"),
            "response_translation": st.column_config.TextColumn("Assistant answer (EN)", width="large"),
            "response_outcome": st.column_config.TextColumn("Response outcome", width="medium"),
            "review_category": st.column_config.TextColumn("Review category", width="medium"),
            "issue_type": st.column_config.TextColumn("Issue type", width="medium"),
            "priority": st.column_config.TextColumn("Priority", width="small"),
            "assigned_to": st.column_config.TextColumn("Assigned to", width="medium"),
            "flagged_by": st.column_config.TextColumn("Flagged by", width="small"),
            "notes": st.column_config.TextColumn("Expert note", width="large"),
            "language": st.column_config.TextColumn("Language", width="small"),
            "topic": st.column_config.TextColumn("Topic", width="large"),
            "knowledge_source_id": st.column_config.TextColumn("Knowledge ID", width="medium"),
            "knowledge_snippet": st.column_config.TextColumn("Knowledge snippet", width="large"),
            "suggested_answer": st.column_config.TextColumn("Expert suggested answer", width="large"),
            "resolution_status": st.column_config.TextColumn("Review status", width="medium"),
        },
    )


def render_charts(df: pd.DataFrame):
    st.subheader("Analytics")
    if df.empty:
        st.info("No data to chart for the current filters.")
        return

    col1, col2 = st.columns(2)
    with col1:
        if "channel_name" in df.columns:
            channel_counts = df["channel_name"].value_counts().reset_index()
            channel_counts.columns = ["channel_name", "count"]
            fig = px.bar(
                channel_counts,
                x="count",
                y="channel_name",
                orientation="h",
                title="Review items by channel",
                labels={"count": "Items", "channel_name": "Channel"},
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "review_category" in df.columns:
            type_counts = df["review_category"].value_counts().reset_index()
            type_counts.columns = ["review_category", "count"]
            fig = px.pie(
                type_counts,
                values="count",
                names="review_category",
                title="Review category mix",
                color="review_category",
                color_discrete_map=REVIEW_CATEGORY_COLORS,
            )
            st.plotly_chart(fig, use_container_width=True)

    if "timestamp_utc" in df.columns:
        trend = df.copy()
        trend["timestamp_utc"] = pd.to_datetime(trend["timestamp_utc"], errors="coerce")
        trend = trend[trend["timestamp_utc"].notna()]
        if not trend.empty:
            trend["date"] = trend["timestamp_utc"].dt.date
            daily = trend.groupby(["date", "review_category"], dropna=False).size().reset_index(name="count")
            fig = px.line(
                daily,
                x="date",
                y="count",
                color="review_category",
                title="Review items over time",
                labels={"date": "Date", "count": "Items", "review_category": "Review category"},
            )
            st.plotly_chart(fig, use_container_width=True)


def render_patterns(df: pd.DataFrame, recurring_df: pd.DataFrame):
    st.subheader("Knowledge Gap Insights")
    st.caption(
    "Global recurring-query summary from BigQuery for the selected date window. "
    "Sidebar filters affect the review charts below, but this table shows overall recurring patterns."
    "Semantic grouping is a planned next iteration.")

    if not recurring_df.empty:
        st.markdown("**Global recurring problematic query groups**")
        st.dataframe(recurring_df, use_container_width=True, hide_index=True)
    else:
        st.info("No recurring query groups returned by the BigQuery view.")

    if "topic" in df.columns and not df.empty:
        topic_counts = Counter(df["topic"].dropna().astype(str))
        topic_df = pd.DataFrame(topic_counts.most_common(15), columns=["topic", "count"])
        fig = px.bar(
            topic_df,
            x="count",
            y="topic",
            orientation="h",
            title="Review items by synthetic topic",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_all_conversations(df: pd.DataFrame):
    st.subheader("All Synthetic Support Conversations")
    if df.empty:
        st.info("No conversations match the current filters.")
        return

    show_translations = st.checkbox("Show English translations", value=False, key="conversations_show_translations")
    display_columns = [
        "timestamp_utc",
        "channel_name",
        "audience_type",
        "conversation_ref",
        "language",
        "user_request",
    ]
    if show_translations:
        display_columns.append("query_translation")
    display_columns.append("bot_response")
    if show_translations:
        display_columns.append("response_translation")
    display_columns.extend(
        [
            "response_outcome",
            "topic",
            "knowledge_source_id",
        ]
    )
    display_columns = [col for col in display_columns if col in df.columns]
    table = df[display_columns].copy()
    if "timestamp_utc" in table.columns:
        table["timestamp_utc"] = pd.to_datetime(table["timestamp_utc"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp_utc": st.column_config.TextColumn("Timestamp", width="medium"),
            "channel_name": st.column_config.TextColumn("Channel", width="medium"),
            "audience_type": st.column_config.TextColumn("Requester type", width="medium"),
            "conversation_ref": st.column_config.TextColumn("Synthetic conversation", width="medium"),
            "language": st.column_config.TextColumn("Language", width="small"),
            "user_request": st.column_config.TextColumn("User request", width="large"),
            "query_translation": st.column_config.TextColumn("User request (EN)", width="large"),
            "bot_response": st.column_config.TextColumn("Assistant answer", width="large"),
            "response_translation": st.column_config.TextColumn("Assistant answer (EN)", width="large"),
            "response_outcome": st.column_config.TextColumn("Response outcome", width="medium"),
            "topic": st.column_config.TextColumn("Topic", width="large"),
            "knowledge_source_id": st.column_config.TextColumn("Knowledge ID", width="medium"),
        },
    )

    csv = table.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered synthetic conversations",
        data=csv,
        file_name="synthetic_conversations_filtered.csv",
        mime="text/csv",
    )


def main():
    st.title("Content Intelligence Dashboard")
    st.caption("A synthetic demo of the review layer behind AI support: customer questions, bot failures, expert feedback, knowledge gaps, and what to fix next.")

    config = load_config()

    try:
        min_date, max_date = get_available_date_range(
            config.project_id,
            config.dataset_id,
            config.location,
            config.conversations_view,
            config.max_bytes_billed,
        )
    except Exception as exc:
        st.error("Could not read the configured BigQuery demo views.")
        st.code(str(exc), language="text")
        st.info("See README.md for setup instructions.")
        st.stop()

    selected_range = st.sidebar.date_input(
        "BigQuery date window",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="bq_date_window",
    )
    if not isinstance(selected_range, tuple) or len(selected_range) != 2:
        start_date, end_date = min_date, max_date
    else:
        start_date, end_date = selected_range

    try:
        with st.spinner("Querying BigQuery demo views..."):
            review_df = load_review_items(
                config.project_id,
                config.dataset_id,
                config.location,
                config.review_view,
                config.max_bytes_billed,
                start_date,
                end_date,
            )
            all_conv_df = load_all_conversations(
                config.project_id,
                config.dataset_id,
                config.location,
                config.conversations_view,
                config.max_bytes_billed,
                start_date,
                end_date,
            )
            recurring_df = load_recurring_summary(
                config.project_id,
                config.dataset_id,
                config.location,
                config.recurring_view,
                config.max_bytes_billed,
                start_date,
                end_date,
            )
    except Exception as exc:
        st.error("BigQuery query failed.")
        st.code(str(exc), language="text")
        st.stop()

    filters = render_sidebar_filters(review_df, all_conv_df)
    filtered_review = apply_filters(review_df, filters)
    filtered_conversations = apply_filters(all_conv_df, filters)

    render_demo_guide()
    render_summary_metrics(filtered_review)
    st.divider()

    tab_review, tab_analytics, tab_patterns, tab_conversations = st.tabs(
        ["Review Queue", "Analytics", "Knowledge Gap Insights", "All Conversations"]
    )
    with tab_review:
        render_review_table(filtered_review)
    with tab_analytics:
        render_charts(filtered_review)
    with tab_patterns:
        render_patterns(filtered_review, recurring_df)
    with tab_conversations:
        render_all_conversations(filtered_conversations)

    st.caption(f"Read-only synthetic demo. Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()

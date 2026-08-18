# Roadmap

This roadmap tracks planned improvements for the Content Intelligence Dashboard demo.

Current baseline:

```text
synthetic support data -> BigQuery tables -> GoogleSQL views -> Streamlit dashboard
```

The goal is to evolve the dashboard from a review table into a lightweight operating layer for AI support quality:

```text
support signal -> review -> diagnosis -> owner -> follow-up -> retest -> monitor
```

---


# Epic 1: Search and investigation workflow

## CID-001 Add keyword and keyphrase search

**Status:** Planned
**Priority:** High
**Effort:** Small / Medium

### Problem

Reviewers need a fast way to pull queries and investigate known topics, product terms, errors, or customer wording.

### Scope

Add a search box across:

* `user_request`
* `query_translation`
* `bot_response`
* `response_translation`
* `notes`
* `suggested_answer`
* `topic`
* `knowledge_source_id`
* `knowledge_snippet`

### Acceptance criteria

* Search works in Review Queue.
* Search works in All Conversations.
* Search combines with existing filters.
* Empty search returns the normal filtered dataset.
* UI explains which fields are searched.

---

## CID-002 Add search result count and visible search state

**Status:** Planned
**Priority:** Medium
**Effort:** Small

### Problem

After searching, reviewers should immediately know how much data matched.

### Scope

Show:

* active search phrase
* number of matching review items
* number of matching conversations

### Acceptance criteria

* Search count updates when filters change.
* Search state is visible above the relevant table.
* Clear empty-state message appears when nothing matches.

## CID-003 Add semantic search experiment

**Status:** Planned
**Priority:** High
**Effort:** Medium / Large

### Problem

Keyword search is useful when reviewers know the exact wording, but users often describe the same issue in different ways.

The dashboard should eventually support semantic search so reviewers can find related questions even when they do not share the same keywords.

### Scope

Add an experimental semantic search workflow for user queries.

Initial version can run locally or as a separate script before being integrated into the Streamlit UI.

Possible approach:

* create embeddings for synthetic user queries
* store embeddings locally or in a lightweight vector index
* allow a reviewer to enter a query
* return semantically similar synthetic queries
* show similarity score, topic, language, response outcome, and storyline ID

### Acceptance criteria
* Semantic search can return related queries with different wording.
* Results include original query, similar query, topic, language, response outcome, and similarity score.
* Semantic search is clearly marked as experimental.
* The implementation does not require production data.
* README or roadmap explains how this differs from keyword search.

## CID-004 Compare keyword search vs semantic search

**Status:** Planned
**Priority:** Medium
**Effort:** Medium

### Problem

Keyword search and semantic search solve different problems. The demo should make that difference visible.

Keyword search finds exact wording. Semantic search finds related intent.

### Scope

Add a comparison workflow using the synthetic / golden dataset.

Example:

* keyword search for retry-after
* semantic search for API is rate limiting me
* compare which related queries each method finds

### Acceptance criteria
* At least 3 example comparisons are documented.
* Semantic search finds at least some related queries that keyword search misses.
* Keyword search remains available for exact investigation.
* Limitations are documented clearly.

## CID-005 Add semantic query clusters

**Status:** Planned
**Priority:** High
**Effort:** Medium / Large

### Problem

Search helps investigate one issue at a time, but reviewers also need to see repeated themes across many conversations.

Current recurring-query logic uses simple normalized text grouping, which can miss similar questions phrased differently.

### Scope

Create semantic clusters of related user queries.

Cluster output should include:

* cluster_id
* cluster_label
* representative query
* related queries
* topic
* query count
* languages
* channels
* review signals
* knowledge gap count
* answer-quality issue count
* recommended fix type
* suggested owner

### Acceptance criteria
* Similar queries can be grouped even when wording differs.
* Each cluster has representative examples.
* Cluster results can be inspected in the dashboard or exported as a file.
* Clusters can be compared against the golden dataset.
* The feature is documented as experimental.

## CID-007 Add cluster detail view

**Status:** Planned
**Priority:** Medium / High
**Effort:** Medium

### Problem

A cluster summary is not enough to decide what to fix.

Reviewers need to inspect evidence before turning a cluster into a docs issue, support note, product feedback item, or retest set.

### Scope

Add a cluster detail view showing:

* cluster label
* short summary
* representative user questions
* assistant response examples
* response outcomes
* expert notes
* languages
* channels
* likely root cause
* recommended fix type
* suggested owner

### Acceptance criteria
* Reviewer can inspect cluster evidence.
* View shows at least 3 representative examples where available.
* View includes suggested fix type and owner.
* View can later feed into docs issue draft generation.
---

# Epic 2: Synthetic dataset and golden query expansion

## CID-008 — Expand synthetic storylines into golden query dataset

**Status:** Planned
**Priority:** High
**Effort:** Medium

### Problem

Current synthetic storylines are useful, but semantic clustering and evaluation need richer query variation and expected labels.

### Scope

Create a golden query dataset with 10–25 realistic multilingual variants per storyline.

Each row should include:

* `golden_query_id`
* `synthetic_storyline_id`
* `query_text`
* `language`
* `expected_topic`
* `expected_response_outcome`
* `expected_fix_type`
* `expected_source_id`
* `expected_owner`
* `notes`

### Acceptance criteria

* Dataset exists as CSV or JSON.
* Each query links to a storyline.
* Each query expected topic and fix type.
* 30% of variants per storyline are in languages other than EN, each non-EN variant has an EN translation.
* Each assistant EN answer is translated into all the languages present in the dataset.
* Dataset can be used locally for clustering / RAG experiments.
* Dataset is clearly marked as synthetic.

---

## CID-009 Add golden dataset loading script

**Status:** Planned
**Priority:** Medium
**Effort:** Medium

### Problem

The golden dataset should be reusable, not just a static file.

### Scope

Add a script to load the golden query dataset into BigQuery or prepare it for local embedding experiments.

### Acceptance criteria

* Script validates required fields.
* Script fails clearly if required fields are missing.
* README or runbook explains how to use it.
* Dataset can be regenerated or reloaded without manual cleanup.

---

# Epic 3: Improve ownership and triage logic

## CID-010 Add `fix_type` concept

**Status:** Planned
**Priority:** High
**Effort:** Medium

### Problem

Not every AI support failure is a content problem. Some require prompt changes, routing fixes, escalation rules, product clarification, or further QA.

### Scope

Add `fix_type` as a dashboard concept.

Suggested values:

* `Knowledge update`
* `Prompt change`
* `Routing fix`
* `Escalation rule`
* `Product clarification`
* `Bug / integration issue`
* `Further QA`
* `No action`

### Acceptance criteria

* `fix_type` appears in review data.
* `fix_type` can be filtered.
* `fix_type` appears in issue drafts.
* Data dictionary explains the difference between `issue_type`, `review_category`, and `fix_type`.

---

## CID-011 Add fix-type summary metrics

**Status:** Planned
**Priority:** Medium
**Effort:** Small / Medium

### Problem

Reviewers need to see where work is accumulating.

### Scope

Add a chart or summary table showing review items by `fix_type`.

### Acceptance criteria

* Summary updates with filters.
* Empty state is handled.
* Chart/table is clearly labeled.
* Fix-type distribution helps identify whether the backlog is mostly docs, prompt, routing, product, or QA work.

---

# Epic 4: Follow-up draft generation

## CID-012 Add static docs issue template

**Status:** Planned
**Priority:** High
**Effort:** Small

### Problem

The dashboard should show how review findings can become clear follow-up work.

### Scope

Add a Markdown template file:

```text
templates/github-docs-issue-template.md
```

Template sections:

* Problem
* Evidence
* Current assistant behavior
* Expert notes
* Likely root cause
* Suggested follow-up
* Acceptance criteria
* Retest queries

### Acceptance criteria

* Template exists in repo.
* Template is written for docs / knowledge follow-up.
* Template can be reused by future issue draft generation.
* Template does not assume automatic GitHub posting.

---

## CID-013 Generate Markdown docs issue draft from selected rows

**Status:** Planned
**Priority:** High
**Effort:** Medium

### Problem

If the fix belongs to documentation update, reviewers still need to manually turn dashboard evidence into a clean docs issue.

### Scope

Add a read-only “Generate docs issue draft” feature.

Inputs:

* selected review rows
* user queries
* assistant answers
* expert notes
* suggested answer
* topic
* source ID / snippet
* issue type
* fix type
* priority
* owner

Output:

* Markdown issue draft
* copyable text
* downloadable `.md` file

### Acceptance criteria

* Reviewer can generate a draft without external write permissions.
* Draft includes representative user queries.
* Draft includes current assistant behavior.
* Draft includes expert notes when available.
* Draft includes likely root cause and suggested follow-up.
* Draft includes acceptance criteria.
* Public demo remains read-only.

---

## CID-014 Generate product feedback summary draft

**Status:** Planned
**Priority:** Medium
**Effort:** Medium

### Problem

Some support issues are product signals, not docs issues.

### Scope

Add a second draft type for product feedback.

Template sections:

* What users are trying to do
* Where they get stuck
* Evidence from support conversations
* Why this may be product-related
* Suggested product / UX follow-up
* Related docs or support workaround

### Acceptance criteria

* Draft can be generated from selected rows or cluster.
* Draft does not overstate support data as final product truth.
* Output is copyable / downloadable Markdown.
* Public demo does not post to external systems.

---

# Epic 5: Retesting and validation

## CID-015 Export selected rows as retest set

**Status:** Planned
**Priority:** Medium / High
**Effort:** Medium

### Problem

After a content, prompt, routing, or product change, teams need to retest the same problem.

### Scope

Allow selected rows or clusters to be exported as a retest dataset.

Suggested fields:

* `id_number`
* `source_interaction_id`
* `user_query` (= `question`)
* `language`
* `topic`
* `expected_response_outcome`
* `expected_source_id`
* `expected_answer_notes`
* `original_failure_type`
* `fix_type`
* `priority`

### Acceptance criteria

* Reviewer can select rows or clusters.
* Export works as CSV.
* Export includes expected behavior.
* Export format is documented.
* Output can be used by FAQ Processor / batch evaluation workflow without further editing.

---

## CID-016 Add before/after validation view

**Status:** Planned
**Priority:** Medium
**Effort:** Medium / Large

### Problem

The dashboard should help show whether changes worked, not only what is broken.

### Scope

Add a before/after comparison view for selected topic, cluster, or date range.

Possible comparisons:

* knowledge-not-found count
* answer-quality issue count
* review status changes
* recurring issue volume
* response outcome mix

### Acceptance criteria

* Reviewer can select before and after periods.
* View shows at least 3 comparison metrics.
* Metrics are clearly labeled as synthetic demo data.
* View supports the loop: identify issue → change something → validate result.

---

# Epic 8: Source coverage and knowledge freshness

## CID-017 Add source coverage view

**Status:** Planned
**Priority:** Medium
**Effort:** Medium

### Problem

AI support quality depends on source coverage and source quality.

### Scope

Add a view grouping review items by `knowledge_source_id`.

Show:

* source ID
* related topics
* issue count
* knowledge gap count
* answer-quality issue count
* latest issue date
* example query

### Acceptance criteria

* Reviewer can see which sources are linked to repeated issues.
* View works with filters.
* View handles missing source IDs.
* Output can support docs issue generation.

---

## CID-018 Add source freshness fields to future data model

**Status:** Planned
**Priority:** Medium
**Effort:** Medium

### Problem

Some AI support issues come from stale or outdated source content.

### Scope

Extend future data model with optional source metadata:

* `source_type`
* `audience`
* `complexity`
* `last_updated`
* `review_status`
* `source_reliability`
* `freshness_status`

### Acceptance criteria

* Proposed fields are documented in data dictionary.
* Fields are optional in first version.
* Roadmap explains how freshness can support review prioritisation.
* No production source data is exposed.

---

# Epic 9: Implementation readiness

## CID-019 Add implementation readiness view

**Status:** Planned
**Priority:** Medium
**Effort:** Medium

### Problem

Before an AI support setup is rolled out to a new customer, audience, language, or channel, teams need a quick readiness picture based on the internal testing and or previous production behavior.

### Scope

Create a readiness summary by channel, audience, language, or topic.

Signals may include:

* unresolved high-priority items
* knowledge gap count
* answer-quality issue count
* recurring query clusters without owner
* fallback / knowledge-not-found rate
* human-review load
* retest status

### Acceptance criteria

* View shows readiness summary for selected segment.
* View highlights top blockers.
* View recommends next actions.
* View is clearly labeled as synthetic demo logic.

---

# Epic 10: Optional external workflow integrations

## CID-020 Optional GitHub issue creation

**Status:** Later
**Priority:** Low / Medium
**Effort:** Large

### Problem

Markdown issue drafts are useful, but real teams may want to post approved issues directly.

### Scope

Add optional GitHub issue creation behind explicit configuration.

### Acceptance criteria

* Feature is disabled by default.
* Public demo does not write to GitHub.
* User must confirm before posting.
* Token/configuration is never committed.
* Generated issue can be previewed before creation.

---

## CID-021 Optional Notion / Linear / Jira draft export

**Status:** Later
**Priority:** Low / Medium
**Effort:** Large

### Problem

Not every follow-up belongs in GitHub. Implementation notes, product feedback, and support playbooks may live in Notion, Linear, Jira, or another system.

### Scope

Support export formats for:

* Notion-style implementation note
* Linear-style product feedback issue
* Jira-style docs/support ticket

Initial version should generate Markdown only.

### Acceptance criteria

* Draft type can be selected.
* Output is copyable / downloadable.
* No external write action in public demo.
* Templates are stored in repo.

---

## CID-022 Optional docs PR draft

**Status:** Later
**Priority:** Low
**Effort:** Large

### Problem

A docs PR is only safe when the system can identify the right file, section, proposed edit, and reviewer.

### Scope

Explore PR draft generation after issue drafts and source mapping are stable.

### Acceptance criteria

* PR draft is not automatic.
* Human approval is required.
* Draft includes evidence and acceptance criteria.
* Feature is clearly marked experimental.

---
## Development order

### Phase 1 — Make the current dashboard easier to investigate
1. CID-001 — Add keyword and keyphrase search
2. CID-002 — Add search result count and visible search state
3. CID-010 — Add fix_type concept
4. CID-011 — Add fix-type summary metrics
### Phase 2 — Prepare follow-up workflow from current review data
5. CID-012 — Add static docs issue template
6. CID-013 — Generate Markdown docs issue draft from selected rows
7. CID-014 — Generate product feedback summary draft
8. CID-015 — Export selected rows as retest set
### Phase 3 — Expand the synthetic dataset for semantic work
9. CID-008 — Expand synthetic storylines into golden query dataset
10. CID-009 — Add golden dataset loading script
### Phase 4 — Add semantic investigation and clustering
11. CID-003 — Add semantic search experiment
12. CID-004 — Compare keyword search vs semantic search
13. CID-005 — Add semantic query clusters
14. CID-007 — Add cluster detail view
### Phase 5 — Add validation and source-quality views
15. CID-016 — Add before/after validation view
16. CID-017 — Add source coverage view
17. CID-018 — Add source freshness fields to future data model
### Phase 6 — Add rollout / implementation-level view
18. CID-019 — Add implementation readiness view
### Phase 7 — Optional external workflow integrations
19. CID-021 — Optional Notion / Linear / Jira draft export
20. CID-020 — Optional GitHub issue creation
21. CID-022 — Optional docs PR draft

### Dependency notes
* CID-001 before CID-002: search needs to exist before search state/counts matter.
* CID-010 before CID-011 / CID-013 / CID-014 / CID-015 / CID-019: fix_type becomes a core field for summaries, drafts, retest sets, and readiness logic.
* CID-012 before CID-013: the static docs issue template should exist before generating issue drafts from rows.
* CID-008 before CID-003 / CID-004 / CID-005 / CID-007: semantic search and clustering need richer query variants and expected labels.
* CID-005 before CID-007: cluster detail view depends on cluster output.
* CID-013 before CID-020 / CID-022: Markdown draft generation should work before any optional GitHub issue creation or PR draft logic.
* CID-015 before CID-016: retest exports make before/after validation more meaningful.
* CID-017 before CID-018 if staying practical-first: source coverage can be added using current source IDs; freshness metadata can come later.
* CID-019 after fix type, retest, clustering, and validation: implementation readiness needs enough signals to summarize meaningfully.
* CID-020 / CID-021 / CID-022 stay later: the public demo should remain read-only until draft generation is stable and clearly separated from external write actions.
---

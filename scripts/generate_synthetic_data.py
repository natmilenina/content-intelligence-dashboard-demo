"""Generate a small synthetic dataset for the BigQuery-backed dashboard demo."""

from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional


HISTORY_DAYS = 45
FEEDBACK_COUNT = 85

INTERACTION_FIELDS = [
    "interaction_id",
    "conversation_id",
    "message_id",
    "timestamp_utc",
    "request_date",
    "channel_id",
    "channel_name",
    "audience_type",
    "conversation_ref",
    "language",
    "user_request",
    "query_translation",
    "bot_response",
    "response_translation",
    "response_outcome",
    "topic",
    "confidence_score",
    "response_latency_ms",
    "knowledge_source_id",
    "knowledge_snippet",
    "fallback_pattern",
    "synthetic_storyline_id",
]

FEEDBACK_FIELDS = [
    "feedback_id",
    "interaction_id",
    "conversation_id",
    "feedback_timestamp",
    "feedback_date",
    "flagged_by",
    "issue_type",
    "review_category",
    "priority",
    "feedback_outcome",
    "suggested_answer",
    "notes",
    "resolution_status",
    "assigned_to",
]


@dataclass(frozen=True)
class Storyline:
    story_id: str
    topic: str
    base_query: str
    correct_answer: str
    wrong_answer: str
    incomplete_answer: str
    unrelated_answer: str
    no_answer_response: str
    suggested_answer: str
    source_id: str
    source_snippet: str


CHANNELS = [
    ("web_chat", "Web Chat", "Customers"),
    ("mobile_app", "Mobile App", "Customers"),
    ("help_center", "Help Center Widget", "Customers"),
    ("developer_portal", "Developer Portal", "Developers"),
    ("partner_portal", "Partner Portal", "Partners"),
    ("support_console", "Support Console", "Internal Support"),
]

LANGUAGES = [
    ("en", "Already English"),
    ("es", "English translation supplied in synthetic data"),
    ("fr", "English translation supplied in synthetic data"),
    ("de", "English translation supplied in synthetic data"),
    ("pt", "English translation supplied in synthetic data"),
    ("ja", "English translation supplied in synthetic data"),
]

STORYLINES = [
    Storyline(
        "story_plan_limits",
        "Plan limits after pricing update",
        "Can I export more than 10 reports on the Starter plan?",
        "Starter includes 10 scheduled exports per month. Users can buy an export pack or move to Growth.",
        "Starter workspaces can create unlimited scheduled exports.",
        "Starter includes scheduled exports.",
        "Open Workspace Settings and change the workspace display name.",
        "I am sorry, I could not find a specific answer about the new Starter export limits.",
        "Starter includes 10 scheduled exports per month. Users can buy an export pack or move to Growth.",
        "kb_plan_exports_2026",
        "Starter includes 10 scheduled exports per month. Export packs and Growth upgrades increase the monthly allowance.",
    ),
    Storyline(
        "story_api_rate_limits",
        "API rate limit retries",
        "What should I do when the Beacon API returns a retry-after header?",
        "Honor the retry-after header, back off exponentially, and retry idempotent requests only.",
        "Ignore the retry-after header and retry the request immediately.",
        "The API has rate limits. Please try again later.",
        "Returns are accepted within 30 days.",
        "I could not find information about retry-after handling for this API.",
        "Honor the retry-after header, back off exponentially, and retry idempotent requests only.",
        "kb_api_retries_2026",
        "Clients should honor retry-after, use exponential backoff, and retry only idempotent requests automatically.",
    ),
    Storyline(
        "story_invoice_exports",
        "Invoice export timing",
        "Why is my invoice export missing today's payments?",
        "Invoice exports are finalized at 02:00 UTC and exclude payments that are still settling.",
        "Invoice exports include all payments immediately after checkout.",
        "Invoice exports are generated daily.",
        "Invite the teammate as a Viewer from Team Settings.",
        "I could not find details about invoice export timing.",
        "Invoice exports are finalized at 02:00 UTC and exclude payments still settling.",
        "kb_invoice_exports_2026",
        "Invoice export files are finalized at 02:00 UTC and may exclude payments that are still settling.",
    ),
    Storyline(
        "story_mobile_login",
        "Passwordless mobile login",
        "How do I recover access if my magic login link expired?",
        "Request a new login link from the same device, then verify with the backup email if needed.",
        "Open account settings and change your password.",
        "Request a new login link.",
        "Partners create sandboxes from Partner Portal > Environments.",
        "I could not find recovery steps for expired magic login links.",
        "Request a new login link from the same device, then verify with the backup email if needed.",
        "kb_passwordless_login_2026",
        "Expired passwordless links should be replaced from the same device, with backup email verification when required.",
    ),
    Storyline(
        "story_returns_exceptions",
        "Return exception policy",
        "Can a damaged item be returned after the 30 day window?",
        "Damaged items can be reviewed up to 60 days with photos and order verification.",
        "Damaged items can never be returned after 30 days.",
        "Returns are accepted within 30 days.",
        "Developers can manage API keys in Developer Portal > API Keys.",
        "I could not find information about damaged-item return exceptions.",
        "Damaged items can be reviewed up to 60 days with photos and order verification.",
        "kb_return_exceptions_2026",
        "Damaged-item exceptions can be reviewed up to 60 days when the customer provides photos and order verification.",
    ),
    Storyline(
        "story_partner_sandbox",
        "Partner sandbox access",
        "Where can a partner create a sandbox account?",
        "Partners create sandboxes from Partner Portal > Environments after invitation approval.",
        "Partners should create a customer account from the public signup page.",
        "Partners can create sandboxes in the Partner Portal.",
        "You can create a customer account from the public signup page.",
        "I could not find partner sandbox setup instructions.",
        "Partners create sandboxes from Partner Portal > Environments after invitation approval.",
        "kb_partner_sandbox_2026",
        "Partner sandboxes are created from Partner Portal > Environments after the partner invitation is approved.",
    ),
]

SUCCESS_QUERIES = [
    (
        "Workspace settings",
        "How do I reset my workspace name?",
        "Open Workspace Settings, choose General, and update the workspace display name.",
        "Open Workspace Settings and choose General.",
        "kb_workspace_settings_2026",
        "Workspace display names are edited from Workspace Settings > General.",
    ),
    (
        "Usage reporting",
        "Where can I download the monthly usage report?",
        "Go to Reports > Usage and choose Download CSV for the selected month.",
        "Go to Reports > Usage.",
        "kb_usage_reports_2026",
        "Monthly usage reports are available from Reports > Usage as downloadable CSV files.",
    ),
    (
        "Team permissions",
        "Can I invite a teammate with view-only access?",
        "Yes. Invite the teammate as a Viewer from Team Settings.",
        "Yes. Invite the teammate from Team Settings.",
        "kb_team_permissions_2026",
        "The Viewer role grants read-only workspace access and can be assigned from Team Settings.",
    ),
    (
        "Notification settings",
        "How do I change notification preferences?",
        "Open Profile > Notifications and adjust email, mobile, and digest settings.",
        "Open Profile > Notifications.",
        "kb_notifications_2026",
        "Users can manage email, mobile, and digest preferences from Profile > Notifications.",
    ),
    (
        "Developer API keys",
        "Where is the API key page?",
        "Developers can manage API keys in Developer Portal > API Keys.",
        "Developers can manage API keys in Developer Portal.",
        "kb_api_keys_2026",
        "API keys are created, rotated, and revoked from Developer Portal > API Keys.",
    ),
    (
        "Seasonal billing pause",
        "Can I pause billing for a seasonal workspace?",
        "Seasonal pause is available on Growth and Enterprise plans from Billing Settings.",
        "Seasonal pause is available from Billing Settings.",
        "kb_seasonal_pause_2026",
        "Growth and Enterprise workspaces can request seasonal billing pause from Billing Settings.",
    ),
]

LANGUAGE_VARIANTS: Dict[str, Dict[str, str]] = {
    "es": {
        "Can I export more than 10 reports on the Starter plan?": "Puedo exportar mas de 10 informes en el plan Starter?",
        "Why is my invoice export missing today's payments?": "Por que mi exportacion de facturas no incluye los pagos de hoy?",
        "How do I recover access if my magic login link expired?": "Como recupero el acceso si expiro mi enlace de inicio de sesion?",
        "Where can I download the monthly usage report?": "Donde puedo descargar el informe mensual de uso?",
    },
    "fr": {
        "Can a damaged item be returned after the 30 day window?": "Un article endommage peut-il etre retourne apres 30 jours?",
        "Where can a partner create a sandbox account?": "Ou un partenaire peut-il creer un compte sandbox?",
        "Can I invite a teammate with view-only access?": "Puis-je inviter un coequipier avec un acces en lecture seule?",
    },
    "de": {
        "What should I do when the Beacon API returns a retry-after header?": "Was soll ich tun, wenn die Beacon API einen retry-after Header zurueckgibt?",
    },
    "pt": {
        "Why is my invoice export missing today's payments?": "Por que a exportacao da fatura nao mostra os pagamentos de hoje?",
    },
    "ja": {
        "Where can a partner create a sandbox account?": "Partner Portal de sandbox account wa doko de tsukurimasu ka?",
    },
}


ANSWER_VARIANTS: Dict[str, Dict[str, str]] = {
    "es": {
        "Starter includes 10 scheduled exports per month. Users can buy an export pack or move to Growth.": "Starter incluye 10 exportaciones programadas al mes. Puedes comprar un paquete de exportaciones o pasar a Growth.",
        "Starter workspaces can create unlimited scheduled exports.": "Los espacios de trabajo Starter pueden crear exportaciones programadas ilimitadas.",
        "Starter includes scheduled exports.": "Starter incluye exportaciones programadas.",
        "Open Workspace Settings and change the workspace display name.": "Abre Workspace Settings y cambia el nombre visible del espacio de trabajo.",
        "I am sorry, I could not find a specific answer about the new Starter export limits.": "Lo siento, no pude encontrar una respuesta especifica sobre los nuevos limites de exportacion de Starter.",
        "Invoice exports are finalized at 02:00 UTC and exclude payments that are still settling.": "Las exportaciones de facturas se finalizan a las 02:00 UTC y excluyen pagos que aun se estan liquidando.",
        "Invoice exports are finalized at 02:00 UTC and exclude payments still settling.": "Las exportaciones de facturas se finalizan a las 02:00 UTC y excluyen pagos que aun se estan liquidando.",
        "Invoice exports include all payments immediately after checkout.": "Las exportaciones de facturas incluyen todos los pagos inmediatamente despues del checkout.",
        "Invoice exports are generated daily.": "Las exportaciones de facturas se generan a diario.",
        "Invite the teammate as a Viewer from Team Settings.": "Invita al companero como Viewer desde Team Settings.",
        "I could not find details about invoice export timing.": "No pude encontrar detalles sobre el horario de exportacion de facturas.",
        "Request a new login link from the same device, then verify with the backup email if needed.": "Solicita un nuevo enlace de inicio de sesion desde el mismo dispositivo y verifica con el correo de respaldo si es necesario.",
        "Open account settings and change your password.": "Abre la configuracion de la cuenta y cambia tu contrasena.",
        "Request a new login link.": "Solicita un nuevo enlace de inicio de sesion.",
        "Partners create sandboxes from Partner Portal > Environments.": "Los partners crean sandboxes desde Partner Portal > Environments.",
        "I could not find recovery steps for expired magic login links.": "No pude encontrar pasos de recuperacion para enlaces magicos vencidos.",
        "Go to Reports > Usage and choose Download CSV for the selected month.": "Ve a Reports > Usage y elige Download CSV para el mes seleccionado.",
        "Go to Reports > Usage.": "Ve a Reports > Usage.",
        "I could not find information about usage reporting.": "No pude encontrar informacion sobre reportes de uso.",
    },
    "fr": {
        "Damaged items can be reviewed up to 60 days with photos and order verification.": "Les articles endommages peuvent etre examines jusqu'a 60 jours avec photos et verification de commande.",
        "Damaged items can never be returned after 30 days.": "Les articles endommages ne peuvent jamais etre retournes apres 30 jours.",
        "Returns are accepted within 30 days.": "Les retours sont acceptes sous 30 jours.",
        "Developers can manage API keys in Developer Portal > API Keys.": "Les developpeurs peuvent gerer les cles API dans Developer Portal > API Keys.",
        "I could not find information about damaged-item return exceptions.": "Je n'ai pas trouve d'informations sur les exceptions de retour pour articles endommages.",
        "Partners create sandboxes from Partner Portal > Environments after invitation approval.": "Les partenaires creent des sandboxes dans Partner Portal > Environments apres approbation de l'invitation.",
        "Partners should create a customer account from the public signup page.": "Les partenaires doivent creer un compte client depuis la page publique d'inscription.",
        "Partners can create sandboxes in the Partner Portal.": "Les partenaires peuvent creer des sandboxes dans le Partner Portal.",
        "You can create a customer account from the public signup page.": "Vous pouvez creer un compte client depuis la page publique d'inscription.",
        "I could not find partner sandbox setup instructions.": "Je n'ai pas trouve les instructions de configuration du sandbox partenaire.",
        "Yes. Invite the teammate as a Viewer from Team Settings.": "Oui. Invitez le coequipier comme Viewer depuis Team Settings.",
        "Yes. Invite the teammate from Team Settings.": "Oui. Invitez le coequipier depuis Team Settings.",
        "I could not find information about team permissions.": "Je n'ai pas trouve d'informations sur les autorisations d'equipe.",
    },
    "de": {
        "Honor the retry-after header, back off exponentially, and retry idempotent requests only.": "Beachte den retry-after Header, verwende exponentielles Backoff und wiederhole nur idempotente Anfragen.",
        "Ignore the retry-after header and retry the request immediately.": "Ignoriere den retry-after Header und wiederhole die Anfrage sofort.",
        "The API has rate limits. Please try again later.": "Die API hat Rate Limits. Bitte versuche es spaeter erneut.",
        "Returns are accepted within 30 days.": "Rueckgaben werden innerhalb von 30 Tagen akzeptiert.",
        "I could not find information about retry-after handling for this API.": "Ich konnte keine Informationen zum retry-after Handling fuer diese API finden.",
    },
    "pt": {
        "Invoice exports are finalized at 02:00 UTC and exclude payments that are still settling.": "As exportacoes de faturas sao finalizadas as 02:00 UTC e excluem pagamentos ainda em liquidacao.",
        "Invoice exports are finalized at 02:00 UTC and exclude payments still settling.": "As exportacoes de faturas sao finalizadas as 02:00 UTC e excluem pagamentos ainda em liquidacao.",
        "Invoice exports include all payments immediately after checkout.": "As exportacoes de faturas incluem todos os pagamentos imediatamente apos o checkout.",
        "Invoice exports are generated daily.": "As exportacoes de faturas sao geradas diariamente.",
        "Invite the teammate as a Viewer from Team Settings.": "Convide o colega como Viewer em Team Settings.",
        "I could not find details about invoice export timing.": "Nao encontrei detalhes sobre o horario de exportacao de faturas.",
    },
    "ja": {
        "Partners create sandboxes from Partner Portal > Environments after invitation approval.": "Partner wa shotai shonin go ni Partner Portal > Environments kara sandbox o sakusei shimasu.",
        "Partners should create a customer account from the public signup page.": "Partner wa kokai signup page kara customer account o sakusei suru hitsuyo ga arimasu.",
        "Partners can create sandboxes in the Partner Portal.": "Partner wa Partner Portal de sandbox o sakusei dekimasu.",
        "You can create a customer account from the public signup page.": "Kokai signup page kara customer account o sakusei dekimasu.",
        "I could not find partner sandbox setup instructions.": "Partner sandbox setup no tetsuzuki ga mitsukarimasen deshita.",
    },
}


def localized_query(base_query: str, language: str) -> str:
    return LANGUAGE_VARIANTS.get(language, {}).get(base_query, base_query)


def localized_answer(answer: str, language: str) -> str:
    return ANSWER_VARIANTS.get(language, {}).get(answer, answer)


def choose_language_for_interaction(base_query: str, answer: str) -> str:
    available_languages = ["en"] + sorted(
        language
        for language, variants in LANGUAGE_VARIANTS.items()
        if base_query in variants and answer in ANSWER_VARIANTS.get(language, {})
    )
    return random.choice(available_languages)


NO_SOURCE_SNIPPET = "No matching knowledge source was retrieved for this synthetic interaction."

ISSUE_NOTES = {
    "Wrong answer": [
        "The answer is inaccurate for this request.",
        "The response gives the wrong operational guidance.",
        "The answer should be replaced with the approved guidance.",
    ],
    "Incomplete answer": [
        "The answer is missing an important condition.",
        "The answer is directionally useful but incomplete.",
        "The answer needs one more detail.",
    ],
    "Unrelated answer": [
        "The answer is unrelated to the user's request.",
        "The response matched the request to the wrong topic.",
        "The response does not address the support question.",
    ],
    "Presentation issue": [
        "The answer is correct, but formatting was broken in the chat message.",
        "The answer needs minor cleanup before reuse.",
        "The answer is usable after a small clarity edit.",
    ],
}

ISSUE_REVIEW_CATEGORIES = {
    "Wrong answer": "Answer quality",
    "Incomplete answer": "Answer quality",
    "Unrelated answer": "Answer quality",
    "Presentation issue": "Presentation cleanup",
}

ISSUE_OUTCOMES = {
    "Wrong answer": "answer_revision_requested",
    "Incomplete answer": "answer_revision_requested",
    "Unrelated answer": "answer_revision_requested",
    "Presentation issue": "minor_presentation_cleanup",
}


def write_csv(path: Path, fields: List[str], rows: Iterable[Dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def parse_reference_datetime(reference_date: Optional[str]) -> datetime:
    if not reference_date:
        return datetime.now(timezone.utc)

    value = reference_date.strip()
    try:
        if "T" not in value and " " not in value:
            parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
            return datetime.combine(parsed_date, datetime.max.time(), tzinfo=timezone.utc).replace(microsecond=0)

        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise ValueError("Use --reference-date as YYYY-MM-DD or an ISO datetime.") from exc


def generate_interactions(count: int, seed: int, reference_datetime: datetime) -> List[Dict]:
    random.seed(seed)
    end = reference_datetime.astimezone(timezone.utc)
    start = end - timedelta(days=HISTORY_DAYS)
    window_seconds = int((end - start).total_seconds())
    rows: List[Dict] = []
    for idx in range(count):
        channel_id, channel_name, audience_type = random.choice(CHANNELS)
        timestamp = start + timedelta(seconds=random.randint(0, window_seconds))

        use_storyline = idx < int(count * 0.62)
        if use_storyline:
            story = STORYLINES[idx % len(STORYLINES)]
            scenario = random.choices(
                [
                    "answered_correct",
                    "answered_wrong",
                    "answered_incomplete",
                    "answered_unrelated",
                    "knowledge_not_found",
                ],
                weights=[32, 16, 18, 10, 24],
            )[0]
            base_query = story.base_query
            topic = story.topic
            story_id = story.story_id

            if scenario == "knowledge_not_found":
                response_outcome = "knowledge_not_found"
                bot_response_en = story.no_answer_response
                confidence = round(random.uniform(0.12, 0.44), 2)
                source_id = ""
                knowledge_snippet = NO_SOURCE_SNIPPET
                fallback_pattern = "specific_answer_not_found"
                feedback_issue_type = ""
                suggested_answer = ""
            else:
                response_outcome = "answered"
                source_id = story.source_id
                knowledge_snippet = story.source_snippet
                fallback_pattern = ""
                suggested_answer = story.suggested_answer

                if scenario == "answered_wrong":
                    bot_response_en = story.wrong_answer
                    confidence = round(random.uniform(0.42, 0.72), 2)
                    feedback_issue_type = "Wrong answer"
                elif scenario == "answered_incomplete":
                    bot_response_en = story.incomplete_answer
                    confidence = round(random.uniform(0.48, 0.78), 2)
                    feedback_issue_type = "Incomplete answer"
                elif scenario == "answered_unrelated":
                    bot_response_en = story.unrelated_answer
                    confidence = round(random.uniform(0.34, 0.68), 2)
                    feedback_issue_type = "Unrelated answer"
                else:
                    bot_response_en = story.correct_answer
                    confidence = round(random.uniform(0.78, 0.98), 2)
                    feedback_issue_type = "Presentation issue" if random.random() < 0.14 else ""
        else:
            topic, base_query, answer, incomplete_answer, source_id, knowledge_snippet = random.choice(SUCCESS_QUERIES)
            scenario = random.choices(
                ["answered_correct", "answered_incomplete", "knowledge_not_found"],
                weights=[82, 10, 8],
            )[0]
            story_id = "story_successful_answer"

            if scenario == "knowledge_not_found":
                response_outcome = "knowledge_not_found"
                bot_response_en = f"I could not find information about {topic.lower()}."
                confidence = round(random.uniform(0.14, 0.42), 2)
                source_id = ""
                knowledge_snippet = NO_SOURCE_SNIPPET
                fallback_pattern = "specific_answer_not_found"
                feedback_issue_type = ""
                suggested_answer = ""
            elif scenario == "answered_incomplete":
                response_outcome = "answered"
                bot_response_en = incomplete_answer
                confidence = round(random.uniform(0.58, 0.78), 2)
                fallback_pattern = ""
                feedback_issue_type = "Incomplete answer"
                suggested_answer = answer
            else:
                response_outcome = "answered"
                bot_response_en = answer
                confidence = round(random.uniform(0.82, 0.99), 2)
                fallback_pattern = ""
                feedback_issue_type = "Presentation issue" if random.random() < 0.10 else ""
                suggested_answer = answer

        language = choose_language_for_interaction(base_query, bot_response_en)
        user_request = localized_query(base_query, language)
        query_translation = base_query if language != "en" else "Already English"
        bot_response = localized_answer(bot_response_en, language)
        response_translation = bot_response_en if language != "en" else "Already English"

        interaction_id = f"int_{idx + 1:04d}"
        conversation_id = f"conv_{channel_id}_{idx + 1:04d}"
        message_id = f"msg_{idx + 1:05d}"
        rows.append(
            {
                "interaction_id": interaction_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "timestamp_utc": timestamp.isoformat(),
                "request_date": timestamp.date().isoformat(),
                "channel_id": channel_id,
                "channel_name": channel_name,
                "audience_type": audience_type,
                "conversation_ref": f"SYNTH-CHAT-{idx + 1:04d}",
                "language": language,
                "user_request": user_request,
                "query_translation": query_translation,
                "bot_response": bot_response,
                "response_translation": response_translation,
                "response_outcome": response_outcome,
                "topic": topic,
                "confidence_score": confidence,
                "response_latency_ms": random.randint(650, 6200),
                "knowledge_source_id": source_id,
                "knowledge_snippet": knowledge_snippet,
                "fallback_pattern": fallback_pattern,
                "synthetic_storyline_id": story_id,
                "_feedback_issue_type": feedback_issue_type,
                "_suggested_answer": suggested_answer,
            }
        )
    return sorted(rows, key=lambda row: row["timestamp_utc"])


def generate_feedback(interactions: List[Dict], seed: int) -> List[Dict]:
    rng = random.Random(seed + 1)
    feedback_rows: List[Dict] = []
    answer_quality_candidates = [
        row
        for row in interactions
        if row["response_outcome"] == "answered"
        and row.get("_feedback_issue_type") in {"Wrong answer", "Incomplete answer", "Unrelated answer"}
    ]
    presentation_candidates = [
        row
        for row in interactions
        if row["response_outcome"] == "answered" and row.get("_feedback_issue_type") == "Presentation issue"
    ]
    latest_interaction_time = max(datetime.fromisoformat(row["timestamp_utc"]) for row in interactions)
    presentation_count = min(8, len(presentation_candidates), FEEDBACK_COUNT)
    presentation_selected = rng.sample(presentation_candidates, presentation_count)
    remaining_count = FEEDBACK_COUNT - presentation_count
    answer_quality_selected = rng.sample(answer_quality_candidates, min(remaining_count, len(answer_quality_candidates)))
    selected = sorted(
        answer_quality_selected + presentation_selected,
        key=lambda row: row["timestamp_utc"],
    )
    experts = ["Expert 1", "Expert 2", "Expert 3", "Expert 4"]
    statuses = ["New", "In Progress", "Resolved", "Won't Fix"]
    assignees = ["Support Ops", "Docs Team", "Product Liaison", "Developer Relations"]
    for idx, interaction in enumerate(selected):
        issue_type = interaction.get("_feedback_issue_type", "")
        priority = {
            "Wrong answer": rng.choice(["High", "High", "Medium"]),
            "Incomplete answer": rng.choice(["Medium", "Medium", "Low"]),
            "Unrelated answer": rng.choice(["High", "Medium"]),
            "Presentation issue": "Low",
        }[issue_type]
        feedback_time = min(
            datetime.fromisoformat(interaction["timestamp_utc"]) + timedelta(hours=rng.randint(3, 72)),
            latest_interaction_time,
        )
        feedback_rows.append(
            {
                "feedback_id": f"fb_{idx + 1:04d}",
                "interaction_id": interaction["interaction_id"],
                "conversation_id": interaction["conversation_id"],
                "feedback_timestamp": feedback_time.isoformat(),
                "feedback_date": feedback_time.date().isoformat(),
                "flagged_by": rng.choice(experts),
                "issue_type": issue_type,
                "review_category": ISSUE_REVIEW_CATEGORIES[issue_type],
                "priority": priority,
                "feedback_outcome": ISSUE_OUTCOMES[issue_type],
                "suggested_answer": interaction.get("_suggested_answer", ""),
                "notes": rng.choice(ISSUE_NOTES[issue_type]),
                "resolution_status": rng.choices(statuses, weights=[45, 30, 20, 5])[0],
                "assigned_to": rng.choice(assignees),
            }
        )
    return feedback_rows


def generate_files(
    output_dir: Path,
    interactions_count: int,
    seed: int,
    reference_date: Optional[str] = None,
) -> Dict[str, Path]:
    reference_datetime = parse_reference_datetime(reference_date)
    interactions = generate_interactions(interactions_count, seed, reference_datetime)
    feedback = generate_feedback(interactions, seed)
    interactions_path = output_dir / "interactions.csv"
    feedback_path = output_dir / "expert_feedback.csv"
    write_csv(interactions_path, INTERACTION_FIELDS, interactions)
    write_csv(feedback_path, FEEDBACK_FIELDS, feedback)
    return {
        "interactions": interactions_path,
        "expert_feedback": feedback_path,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic dashboard data.")
    parser.add_argument("--output-dir", default="data/synthetic", help="Directory for generated CSV files.")
    parser.add_argument("--interactions", type=int, default=360, help="Number of synthetic interactions.")
    parser.add_argument("--seed", type=int, default=20260809, help="Deterministic random seed.")
    parser.add_argument(
        "--reference-date",
        help="Optional UTC anchor date or ISO datetime for reproducible 45-day demo windows.",
    )
    args = parser.parse_args()

    paths = generate_files(Path(args.output_dir), args.interactions, args.seed, args.reference_date)
    print(f"Generated {paths['interactions']}")
    print(f"Generated {paths['expert_feedback']}")


if __name__ == "__main__":
    main()

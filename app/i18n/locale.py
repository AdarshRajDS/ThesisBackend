"""Shared language lock for RAG, MCP chat, and API responses."""

from __future__ import annotations

from typing import Literal

SupportedLanguage = Literal["en", "de"]
DEFAULT_LANGUAGE: SupportedLanguage = "en"

# Keep in sync with anatomy_mcp/query_validation.CLARIFICATION_MESSAGE (English).
_CLARIFICATION_EN = (
    "Please name a specific structure from the exportable catalog "
    "(e.g. liver, heart, femur.l, left kidney, Angular gyrus.l)."
)
_CLARIFICATION_DE = (
    "Bitte nennen Sie eine konkrete Struktur aus dem exportierbaren Katalog "
    "(z. B. Leber, Herz, femur.l, linke Niere, Angular gyrus.l)."
)

CONSENT_ANSWER: dict[SupportedLanguage, str] = {
    "en": (
        "No content found in the given local resources for this question. "
        "Would you like me to suggest an answer from world knowledge instead?"
    ),
    "de": (
        "Zu dieser Frage wurde in Ihren lokalen Ressourcen kein Inhalt gefunden. "
        "Soll ich stattdessen eine Antwort aus allgemeinem Weltwissen vorschlagen?"
    ),
}

WORLD_KNOWLEDGE_PREFIX: dict[SupportedLanguage, str] = {
    "en": "This answer is outside your anatomy corpus.\n\n",
    "de": "Diese Antwort stammt nicht aus Ihrem Anatomie-Korpus.\n\n",
}

ABSTAIN: dict[SupportedLanguage, str] = {
    "en": "Not found in provided documents",
    "de": "In den bereitgestellten Dokumenten nicht gefunden",
}


def normalize_language(value: str | None) -> SupportedLanguage:
    if not value:
        return DEFAULT_LANGUAGE
    code = value.strip().lower().replace("_", "-").split("-")[0]
    if code == "de":
        return "de"
    return "en"


def clarification_message(language: SupportedLanguage) -> str:
    return _CLARIFICATION_DE if language == "de" else _CLARIFICATION_EN


def resolve_clarification(
    language: SupportedLanguage,
    instruction: str | None = None,
) -> str:
    if instruction and instruction.strip() and instruction.strip() != _CLARIFICATION_EN:
        return instruction.strip()
    return clarification_message(language)


def language_lock_instruction(language: SupportedLanguage) -> str:
    if language == "de":
        return (
            "\n\nSPRACHREGEL (verbindlich): Antworten Sie ausschließlich auf Deutsch. "
            "Alle Erklärungen, Fragen und Kurzantworten müssen auf Deutsch sein. "
            "Katalog-Labels (z. B. femur.l) dürfen unverändert bleiben."
        )
    return (
        "\n\nLANGUAGE RULE (mandatory): Reply only in English. "
        "All explanations, questions, and short answers must be in English. "
        "Catalog labels (e.g. femur.l) may stay as-is."
    )


def consent_answer_text(language: SupportedLanguage) -> str:
    return CONSENT_ANSWER[language]


def world_knowledge_prefix(language: SupportedLanguage) -> str:
    return WORLD_KNOWLEDGE_PREFIX[language]


def abstain_text(language: SupportedLanguage) -> str:
    return ABSTAIN[language]


_MCP_UI: dict[SupportedLanguage, dict[str, str]] = {
    "en": {
        "empty_input": "Describe a structure to export (e.g. liver, femur.l, left kidney).",
        "export_finished": "Export finished. Use the viewer and downloads below.",
        "done": "Done.",
        "no_tools": (
            "The model described export files without running MCP tools. "
            "In LM Studio, enable tool/function calling for your model, then try again."
        ),
        "tool_required": (
            "You must call the appropriate MCP tool(s) before answering. "
            "Start with search_anatomy_catalog if unsure, then export_anatomy_part."
        ),
        "no_mcp_tools_run": (
            "No MCP tools were executed. Enable tool/function calling in LM Studio "
            "and use a model that supports OpenAI-style tools."
        ),
        "mcp_incomplete": (
            "I could not complete this via MCP tools. "
            "Ensure LM Studio is running and supports tool calling."
        ),
        "timeout_retry": (
            "export_anatomy_part timed out. Call export_anatomy_package now for "
            "part_query '{query}' with include_preview false."
        ),
        "loop_ended": (
            "MCP tool loop ended without a final model export.{timeout} "
            "Try a more specific catalog label (e.g. left kidney)."
        ),
        "multiple_matches": (
            'Multiple exportable matches for "{query}". '
            "Pick one exact label: {labels}"
        ),
        "catalog_searched": (
            "Catalog searched: {catalog} (geometry-proven entries from Z-Anatomy {blend})."
        ),
        "no_exact_with_suggestions": (
            'No exact match for "{query}" in {catalog}. '
            "Similar exportable structures: {labels}. "
            "Reply with one exact catalog label to export."
        ),
        "no_exact_with_structured_suggestions": (
            'No exact match for "{query}" in {catalog}. '
            "Exportable alternatives (all verified in exportable_catalog.json):\n{suggestions}\n"
            "Reply with one exact catalog label to export."
        ),
        "no_exact_no_suggestions": (
            'No match for "{query}" in {catalog}. '
            "Try a specific Z-Anatomy label (e.g. femur.l, Hip bone.l, Hip region.l)."
        ),
        "export_failed": "Found {label} in exportable_catalog.json but export failed: {err}.",
        "exported": "Exported {label}.",
        "exported_via": "Exported {label} via {tools}.",
        "mcp_failed": "MCP + LM Studio failed: {err}. Is LM Studio running at {base}?",
    },
    "de": {
        "empty_input": (
            "Beschreiben Sie eine Struktur zum Export "
            "(z. B. Leber, femur.l, linke Niere)."
        ),
        "export_finished": "Export abgeschlossen. Nutzen Sie Viewer und Downloads unten.",
        "done": "Fertig.",
        "no_tools": (
            "Das Modell hat Exportdateien beschrieben, ohne MCP-Tools auszuführen. "
            "Aktivieren Sie in LM Studio Tool-/Function-Calling und versuchen Sie es erneut."
        ),
        "tool_required": (
            "Rufen Sie zuerst die passenden MCP-Tools auf. "
            "Bei Unsicherheit search_anatomy_catalog, dann export_anatomy_part."
        ),
        "no_mcp_tools_run": (
            "Keine MCP-Tools ausgeführt. Aktivieren Sie Tool-/Function-Calling in LM Studio "
            "und verwenden Sie ein Modell mit OpenAI-kompatiblen Tools."
        ),
        "mcp_incomplete": (
            "Über MCP-Tools konnte dies nicht abgeschlossen werden. "
            "LM Studio muss laufen und Tool-Calling unterstützen."
        ),
        "timeout_retry": (
            "export_anatomy_part hat ein Timeout. Rufen Sie jetzt export_anatomy_package auf "
            "für part_query '{query}' mit include_preview false."
        ),
        "loop_ended": (
            "MCP-Tool-Schleife ohne finalen Modell-Export beendet.{timeout} "
            "Versuchen Sie ein genaueres Katalog-Label (z. B. linke Niere)."
        ),
        "multiple_matches": (
            'Mehrere exportierbare Treffer für „{query}". '
            "Wählen Sie ein exaktes Label: {labels}"
        ),
        "catalog_searched": (
            "Durchsuchter Katalog: {catalog} (geometriegeprüfte Einträge aus Z-Anatomy {blend})."
        ),
        "no_exact_with_suggestions": (
            'Kein exakter Treffer für „{query}" im Katalog {catalog}. '
            "Ähnliche exportierbare Strukturen: {labels}. "
            "Bitte ein exaktes Katalog-Label zum Export nennen."
        ),
        "no_exact_with_structured_suggestions": (
            'Kein exakter Treffer für „{query}" im Katalog {catalog}. '
            "Exportierbare Alternativen (geprüft in exportable_catalog.json):\n{suggestions}\n"
            "Bitte ein exaktes Katalog-Label zum Export nennen."
        ),
        "no_exact_no_suggestions": (
            'Kein Treffer für „{query}" im Katalog {catalog}. '
            "Versuchen Sie ein konkretes Z-Anatomy-Label (z. B. femur.l, Hip bone.l, Hip region.l)."
        ),
        "export_failed": (
            "{label} in exportable_catalog.json gefunden, aber Export fehlgeschlagen: {err}."
        ),
        "exported": "{label} exportiert.",
        "exported_via": "{label} exportiert über {tools}.",
        "mcp_failed": "MCP + LM Studio fehlgeschlagen: {err}. Läuft LM Studio unter {base}?",
    },
}


def mcp_ui(language: SupportedLanguage, key: str, **kwargs: str) -> str:
    template = _MCP_UI[language].get(key) or _MCP_UI["en"][key]
    return template.format(**kwargs) if kwargs else template


def build_mcp_system_prompt(language: SupportedLanguage) -> str:
    base = (
        "You are an anatomy assistant connected to local MCP tools and LM Studio. "
        "You must use MCP tools for anatomy catalog search, 3D export, or study packages — "
        "do not answer from general knowledge when the user wants a 3D model or catalog lookup. "
        "Do not claim an export succeeded unless you called export_anatomy_part or export_anatomy_package. "
        "Matching uses exportable_catalog.json (geometry-proven entries from Startup.blend). "
        "Use search_anatomy_catalog when the structure name may be broad, ambiguous, or unfamiliar. "
        "When search or export returns part_not_found, call suggest_exportable_anatomy — "
        "it only returns geometry-proven exportable_catalog.json entries (can_export=true). "
        "Present suggestion labels with match_reason; do not invent anatomy names. "
        "Only auto-export when auto_export_candidate confidence meets auto_export_threshold; "
        "otherwise ask the user to pick an exact label. "
        "If the user message is vague (e.g. 'show me the organ', 'export the part'), do NOT guess part_query; "
        "ask them to name a specific structure (liver, heart, femur.l, left kidney). "
        "If search returns multiple entries, ask the user to pick an exact label before exporting. "
        "Use export_anatomy_part for a single organ export (include_preview=false unless asked). "
        "Prefer export_anatomy_package for large structures (brain, thalamus). "
        "If export_anatomy_part times out, retry with export_anatomy_package. "
        "After a successful export, reply in ONE short sentence (e.g. 'Exported Left kidney.'). "
        "Never list URLs or extra files (objects.json, collections.json, relations.json, manifest, etc.) — "
        "the app UI only shows the annotated viewer, GLB download, and annotations JSON."
    )
    if language == "de":
        base = (
            "Sie sind ein Anatomie-Assistent mit lokalen MCP-Tools und LM Studio. "
            "Nutzen Sie MCP-Tools für Katalogsuche, 3D-Export oder Studienpakete — "
            "antworten Sie nicht aus Allgemeinwissen, wenn der Nutzer ein 3D-Modell oder eine Katalogsuche will. "
            "Behaupten Sie keinen erfolgreichen Export ohne export_anatomy_part oder export_anatomy_package. "
            "Matching nutzt exportable_catalog.json (geometriegeprüfte Einträge aus Startup.blend). "
            "Nutzen Sie search_anatomy_catalog bei breiten oder unklaren Strukturnamen. "
            "Bei part_not_found suggest_exportable_anatomy aufrufen — nur exportierbare Katalogeinträge. "
            "Vorschläge mit match_reason zeigen; keine erfundenen Anatomienamen. "
            "Nur bei auto_export_candidate über auto_export_threshold automatisch exportieren. "
            "Bei vagen Anfragen (z. B. „zeig mir das Organ“) part_query NICHT raten; "
            "bitten Sie um eine konkrete Struktur (Leber, Herz, femur.l, linke Niere). "
            "Bei mehreren Treffern wählen lassen, bevor exportiert wird. "
            "export_anatomy_part für einzelne Organe (include_preview=false, sofern nicht anders gewünscht). "
            "export_anatomy_package für große Strukturen (Gehirn, Thalamus). "
            "Bei Timeout von export_anatomy_part export_anatomy_package versuchen. "
            "Nach erfolgreichem Export EIN kurzer Satz (z. B. „Linke Niere exportiert.“). "
            "Keine URLs oder Zusatzdateien auflisten — die UI zeigt nur Viewer, GLB und Beschriftungs-JSON."
        )
    return base + language_lock_instruction(language)

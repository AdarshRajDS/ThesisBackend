"""
Shared rules for off-topic detection and when document citations may be shown.
"""

from __future__ import annotations

OFF_TOPIC_QUESTION_PATTERNS = (
    "capital of france",
    "fifa world cup",
    "weather forecast",
    "nice 2024",
    "first-line drug for hypertension",
    "crispr",
    "attention is all you need",
    "transformer",
    "lithium-ion",
    "ohm's law",
    "eiffel tower",
    "train for a marathon",
)

DECLINE_PHRASES = (
    "cannot answer",
    "can't answer",
    "does not contain",
    "doesn't contain",
    "not contain any",
    "no content found",
    "cannot provide",
    "unable to answer",
    "outside the scope",
    "not related to",
    "unrelated to",
    "does not address",
    "doesn't address",
    "i cannot answer",
    "i can't answer",
    "does not contain any data",
    "doesn't contain any data",
)

CONSENT_ANSWER_TEXT = (
    "No content found in the given local resources for this question. "
    "Would you like me to suggest an answer from world knowledge instead?"
)


def is_clearly_off_topic_question(question: str) -> bool:
    q = (question or "").lower()
    return any(pattern in q for pattern in OFF_TOPIC_QUESTION_PATTERNS)


def answer_declines_question(answer: str) -> bool:
    a = (answer or "").lower()
    if not a.strip():
        return True

    # Treat as a decline only when the response is mostly a refusal/abstain,
    # not when it contains substantial grounded content plus one "not found" note.
    if any(a.strip().startswith(phrase) for phrase in DECLINE_PHRASES):
        return True

    abstain_markers = (
        "not found in provided documents",
        "in den bereitgestellten dokumenten nicht gefunden",
    )
    if any(marker in a for marker in abstain_markers):
        # If the answer is long, assume partial answer and keep document sources visible.
        if len(a) > 260:
            return False
        # If almost no citation markers appear, it's likely a pure abstain.
        if a.count("[") <= 1:
            return True

    return False


WORLD_KNOWLEDGE_PREFIX = (
    "This answer is outside your anatomy corpus.\n\n"
)


def classify_ooc_topic(question: str) -> str:
    """Subtype for out-of-corpus questions: general_trivia | medical_guideline | scientific."""
    q = (question or "").lower()
    if any(t in q for t in ("nice", "hypertension", "first-line drug", "clinical guideline")):
        return "medical_guideline"
    if any(t in q for t in ("crispr", "gene editing", "genome", "nih", "genetic")):
        return "scientific"
    if any(t in q for t in ("capital of france", "fifa", "weather", "marathon", "eiffel")):
        return "general_trivia"
    return "general"


def authoritative_external_sources(question: str) -> list[str]:
    """
    Curated URLs for world-knowledge mode (not generic search pages).
    """
    q = (question or "").lower()
    topic = classify_ooc_topic(question)

    if topic == "medical_guideline":
        urls = [
            "https://www.nice.org.uk/guidance",
            "https://www.nice.org.uk/guidance/conditions-and-diseases/cardiovascular-conditions/hypertension",
            "https://medlineplus.gov/highbloodpressure.html",
        ]
        if "nice" in q and "2024" in q:
            return urls[:2] + ["https://www.nice.org.uk/guidance/published?type=cks"]
        return urls

    if topic == "scientific":
        urls = [
            "https://www.genome.gov/genetics-glossary/CRISPR",
            "https://medlineplus.gov/genetics/understanding/therapy/genomeediting/",
            "https://www.ncbi.nlm.nih.gov/books/NBK447569/",
        ]
        if "crispr" in q:
            return urls
        return urls

    if topic == "general_trivia":
        return []

    return [
        "https://medlineplus.gov/",
        "https://www.nih.gov/health-information",
    ]


def should_attach_document_sources(
    question: str,
    answer: str,
    *,
    requires_world_knowledge_consent: bool = False,
    world_knowledge_used: bool = False,
    local_content_found: bool = True,
) -> bool:
    """Document quotes are only shown when the answer is truly grounded in the corpus."""
    if requires_world_knowledge_consent or world_knowledge_used:
        return False
    if not local_content_found:
        return False
    if is_clearly_off_topic_question(question):
        return False
    if answer_declines_question(answer):
        return False
    return True

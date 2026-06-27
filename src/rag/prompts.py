"""
Typed prompts for question-type routing.
"""

from __future__ import annotations

from app.i18n.locale import SupportedLanguage, abstain_text, language_lock_instruction
from src.rag.question_classifier import QuestionType

ABSTAIN = "Not found in provided documents"


def build_prompt(
    question_type: QuestionType,
    numbered_passages: str,
    question: str,
    *,
    assumption_note: str | None = None,
    language: SupportedLanguage = "en",
) -> str:
    assumption = f"\nNote: {assumption_note}\n" if assumption_note else ""
    abstain = abstain_text(language)
    lang_rule = language_lock_instruction(language)

    if numbered_passages == "NO_PASSAGES_RETRIEVED":
        return f"""You are a medical anatomy assistant.
No passages were retrieved. Respond exactly with: {abstain}

Question:
{question}
{lang_rule}"""

    base_rules = f"""
You MUST answer using ONLY the numbered passages below.
- Every substantive claim must cite inline markers like [1] or [2].
- If the answer cannot be found in the passages, respond exactly with: {abstain}
- Do not invent quotes; paraphrase only from passage text.
{assumption}
Passages:
{numbered_passages}

Question:
{question}
"""

    if question_type == "simple":
        prompt = f"""You are a medical anatomy assistant. Give a brief, clear answer.
{base_rules}
Keep the answer concise (2–4 sentences)."""

    elif question_type == "complex":
        prompt = f"""You are a medical anatomy assistant. Synthesize information from multiple passages.
{base_rules}
Compare or integrate facts as needed; cite each claim."""

    elif question_type == "thinking":
        prefix = (
            "Basierend auf diesem Verlauf…"
            if language == "de"
            else "Based on this pathway…"
        )
        prompt = f"""You are a medical anatomy assistant.
{base_rules}
When inferring beyond a single sentence, prefix with "{prefix}" or similar."""

    elif question_type == "synthesis":
        prompt = f"""You are a medical anatomy assistant.
{base_rules}
Explain step-by-step (numbered steps). Cite passages at each step."""

    elif question_type == "broad":
        closing = (
            'Ende mit: "Ich kann zu jedem Teil vertiefen — fragen Sie nach einer konkreten Struktur oder einem Prozess."'
            if language == "de"
            else 'End with: "I can go deeper into any one part—ask about a specific structure or process."'
        )
        prompt = f"""You are a medical anatomy assistant.
{base_rules}
This is a broad topic. Give a high-level chapter overview (organization, key structures, main functions).
{closing}
Do not claim to cover "everything." """

    elif question_type == "typo_edge":
        prompt = f"""You are a medical anatomy assistant.
{base_rules}
If spelling was corrected, you may briefly note the intended term."""

    elif question_type == "multimodal_figure":
        prompt = f"""You are a medical anatomy assistant.
{base_rules}
Prioritize figure captions and nearby explanatory text. Describe what the figure shows."""

    else:
        prompt = f"""You are a medical anatomy assistant.
{base_rules}"""

    return prompt + lang_rule


def build_evidence_classifier_prompt(
    question: str,
    numbered_passages: str,
    *,
    language: SupportedLanguage = "en",
) -> str:
    lang_rule = language_lock_instruction(language)
    instruction = (
        "Klassifizieren Sie jeden Passage-Eintrag als A/B/C."
        if language == "de"
        else "Classify each passage as A/B/C."
    )
    return f"""You are an evidence relevance classifier for document-grounded QA.
{instruction}

Question:
{question}

Passages:
{numbered_passages}

Return ONLY strict JSON in this shape:
{{
  "A": [1,2],
  "B": [3],
  "C": [4,5]
}}

Definitions:
- A: directly answers the question
- B: partially relevant background
- C: irrelevant to the question

Do not include explanation text. {lang_rule}"""


def build_grounded_synthesis_prompt(
    question: str,
    allowed_evidence: str,
    *,
    response_style: str | None = None,
    language: SupportedLanguage = "en",
) -> str:
    abstain = abstain_text(language)
    lang_rule = language_lock_instruction(language)
    style_rule = f"\nResponse style requirement:\n{response_style}\n" if response_style else ""
    return f"""You are a document-grounded answer synthesizer.

You may ONLY use information that appears in ALLOWED EVIDENCE.
Do not use outside medical or general knowledge.
Do not infer unsupported facts.
Every factual sentence must include citation markers like [1], [2].

If evidence is insufficient, answer exactly:
{abstain}

Question:
{question}
{style_rule}

ALLOWED EVIDENCE:
{allowed_evidence}

Write a concise educational answer with citations after each claim.
If only part of the question is covered, answer only that supported part and mention what is not supported.
{lang_rule}"""

from app.i18n.locale import (
    clarification_message,
    consent_answer_text,
    normalize_language,
    resolve_clarification,
)


def test_normalize_language():
    assert normalize_language(None) == "en"
    assert normalize_language("en") == "en"
    assert normalize_language("EN") == "en"
    assert normalize_language("de") == "de"
    assert normalize_language("de-DE") == "de"
    assert normalize_language("fr") == "en"


def test_localized_consent_and_clarification():
    assert "Weltwissen" in consent_answer_text("de")
    assert "world knowledge" in consent_answer_text("en")
    assert "Bitte nennen" in clarification_message("de")
    assert resolve_clarification("de", None) == clarification_message("de")

from src.rag.query_policy import (
    answer_declines_question,
    is_clearly_off_topic_question,
    should_attach_document_sources,
)


def test_france_question_is_off_topic():
    assert is_clearly_off_topic_question("What is the capital of France?") is True


def test_france_decline_hides_document_sources():
    answer = (
        "The information provided in the context does not contain any data regarding "
        "the capital of France. I cannot answer the question about the capital of France."
    )
    assert answer_declines_question(answer) is True
    assert (
        should_attach_document_sources(
            "What is the capital of France?",
            answer,
            local_content_found=True,
        )
        is False
    )


def test_anatomy_answer_keeps_document_sources():
    assert (
        should_attach_document_sources(
            "What is the role of the thalamus?",
            "The thalamus relays sensory information to the cerebral cortex.",
            local_content_found=True,
        )
        is True
    )

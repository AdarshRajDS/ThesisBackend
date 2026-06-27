from src.rag.citation_filter import filter_sources_pre_generation, filter_sources_post_generation


def test_toc_filtered_pre_generation():
    sources = [
        {"chunk_preview": "Chapter 1 ..... Chapter 2 ..... Chapter 3", "support_score": 0.9},
        {"chunk_preview": "The brain stem includes midbrain pons and medulla.", "support_score": 0.5},
    ]
    out = filter_sources_pre_generation(sources)
    assert len(out) == 1
    assert "brain stem" in out[0]["chunk_preview"]


def test_post_generation_overlap():
    sources = [
        {"chunk_preview": "The thalamus relays sensory information to the cortex."},
        {"chunk_preview": "Copyright OpenStax all rights reserved."},
    ]
    answer = "The thalamus relays sensory signals to the cerebral cortex."
    out = filter_sources_post_generation(answer, sources)
    assert out is not None
    assert len(out) == 1

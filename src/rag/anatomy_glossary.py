"""
Anatomy term glossary for typo correction and synonym expansion.
"""

from __future__ import annotations

# Canonical term -> variants / common misspellings
GLOSSARY: dict[str, list[str]] = {
    "brain stem": ["brainstem", "brain-stem", "broinstem", "brain stem"],
    "brainstem": ["brain stem", "broinstem"],
    "neuromuscular junction": [
        "neuromuscular junction",
        "neuro muscular junction",
        "nmj",
    ],
    "thalamus": ["thalamus", "thalamous", "thalami"],
    "synapse": ["synapse", "synaps", "synapses"],
    "gray matter": ["gray matter", "grey matter", "gray mater", "grey mater"],
    "white matter": ["white matter", "white mater"],
    "action potential": ["action potential", "action potentials"],
    "graded potential": ["graded potential"],
    "cerebellum": ["cerebellum", "cerebelum"],
    "hypothalamus": ["hypothalamus", "hypothalmus"],
    "upper motor neuron": ["upper motor neuron", "umn"],
    "lower motor neuron": ["lower motor neuron", "lmn"],
    "acetylcholine": ["acetylcholine", "ach"],
    "myelin": ["myelin", "myelination"],
    "oligodendrocyte": ["oligodendrocyte", "oligodendrocytes"],
    "schwann cell": ["schwann cell", "schwann cells"],
    "blood-brain barrier": ["blood brain barrier", "bbb"],
    "end plate potential": ["end plate potential", "epp"],
}


def all_canonical_terms() -> list[str]:
    return list(GLOSSARY.keys())


def variants_for(canonical: str) -> list[str]:
    return GLOSSARY.get(canonical, [canonical])


def lookup_canonical(term: str) -> str | None:
    t = (term or "").lower().strip()
    for canonical, variants in GLOSSARY.items():
        if t == canonical.lower():
            return canonical
        for v in variants:
            if t == v.lower():
                return canonical
    return None


def expand_synonym_query(canonical: str) -> str:
    """Corpus-style query expansion for retrieval."""
    expansions = {
        "brain stem": "brain stem midbrain pons medulla anatomy function",
        "neuromuscular junction": "neuromuscular junction acetylcholine end plate muscle",
        "thalamus": "thalamus sensory relay cerebral cortex",
        "synapse": "synapse neurotransmitter presynaptic postsynaptic",
        "gray matter": "gray matter neuron cell bodies CNS",
        "white matter": "white matter axons myelin CNS",
    }
    return expansions.get(canonical, f"{canonical} anatomy physiology")

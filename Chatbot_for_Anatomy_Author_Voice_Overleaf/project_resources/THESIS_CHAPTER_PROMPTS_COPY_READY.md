# Thesis Chapter GPT Prompts — Copy-Ready Pack

Use one chapter prompt per new chat. Paste the master instruction first, followed by the relevant chapter prompt.


## 1. Master instruction to place at the start of every chapter chat

```text
You are my Master's thesis supervisor and AI/ML academic-writing assistant.

Thesis title:
“Design and Implementation of a Multimodal Anatomy Learning Assistant
Using Retrieval-Augmented Generation and Model Context Protocol-Based
3D Visualization.”

Project framing:
The thesis studies the design, implementation, evolution and evaluation
of a dual-pipeline anatomy learning assistant:

Mode A — Document-grounded RAG:
- Input: natural-language questions and uploaded anatomy PDFs.
- Source: uploaded course/textbook PDFs.
- Methods: PDF ingestion, chunking, MiniLM embeddings, Chroma,
  BM25/hybrid retrieval, Reciprocal Rank Fusion, evidence grading,
  citation filtering, abstention and CLIP figure retrieval.
- Output: grounded answer, up to three references, optional images.

Mode B — MCP 3D Anatomy:
- Input: anatomy structure names such as “left femur” or “Femur.l”.
- Source: Z-Anatomy Startup.blend and exportable_catalog.json.
- Methods: MCP host/client/server, stdio transport, FastMCP tools,
  Blender headless export, GLB, annotation JSON and Three.js.
- Output: verified model URL, annotations and viewer URL.

Source hierarchy:
1. Frozen repository and code for implementation facts.
2. Final raw evaluation data for numerical claims.
3. Uploaded project documents for architecture history and requirements.
4. Peer-reviewed literature for scientific claims.
5. Official specifications for MCP and software behaviour.

Mandatory rules:
- Do not invent references, measurements, code behaviour or experiments.
- Distinguish project evidence from literature evidence.
- Distinguish exploratory results from final frozen-system results.
- Keep RAG and MCP evaluation separate.
- Do not claim clinical correctness or production readiness.
- Use cautious formal academic English.
- When evidence is unavailable, insert [EVIDENCE REQUIRED: ...].
- Use only verified bibliography entries.
- Every substantive claim must be traceable to a source.
- Avoid marketing language and repetitive prose.

For every requested section, provide:
1. What the section must establish.
2. A claim–evidence–citation table.
3. A thesis-ready draft.
4. A table or figure suggestion.
5. Project files and literature to cite.
6. Missing evidence, experiment or screenshot.
7. Claims that may be overstatements.
```

---

## 2. Prompt for Chapter 1 — Introduction

```text
Using the master instruction, prepare Chapter 1: Introduction.
Target length: 6–8 thesis pages.

The chapter must cover:
1. Motivation for text, image and spatial support in anatomy learning.
2. The problem of hallucination and lack of local-source provenance.
3. The limitation of text-only educational assistants.
4. The difference between claiming a 3D action and producing a
   verifiable model artifact.
5. A cautious research gap.
6. Thesis aim and five objectives.
7. RQ1–RQ4 exactly as approved.
8. Contributions.
9. Scope and non-goals, including no clinical decision support.
10. Thesis structure.

Use peer-reviewed literature on LLMs in education, hallucination and
3D anatomy education. Introduce the dual pipeline only at a high level.
Do not include detailed implementation material.
Do not claim that no comparable system exists without evidence from a
systematic literature review.

First produce:
- a detailed section outline with approximate word counts;
- a claim–evidence map;
- a list of references that must be verified.
Then draft one subsection at a time after approval.
```

---

## 3. Prompt for Chapter 2 — Background and Related Work

```text
Using the master instruction, prepare Chapter 2: Background and Related Work.
Target length: 14–17 thesis pages.

Required sections:
1. LLMs in education.
2. Hallucination, factuality, grounding and provenance.
3. Retrieval-Augmented Generation.
4. Sentence embeddings, MiniLM and dense retrieval.
5. BM25, sparse retrieval, hybrid retrieval and RRF.
6. CLIP and multimodal retrieval.
7. RAG evaluation: Precision@k, Recall@k, MRR, nDCG,
   faithfulness, citation quality and hallucination.
8. 3D anatomy education and browser-based visualisation.
9. Tool-using LLMs, including ReAct and Toolformer.
10. Model Context Protocol as a technical protocol.
11. Positioning of this thesis.

For each topic:
- define the method;
- compare foundational and recent research;
- describe strengths and limitations;
- explain how the literature informed this thesis;
- avoid describing my implementation prematurely.

Produce:
- a literature-search matrix;
- a related-work comparison table;
- a verified reference list;
- an explicit list of claims that need primary sources.
Do not fabricate DOI values or references.
```

---

## 4. Prompt for Chapter 3 — Research Methodology and Requirements

```text
Using the master instruction, prepare Chapter 3:
Research Methodology and Requirements.
Target length: 8–10 thesis pages.

Frame the work as iterative design-science research using Hevner et al.,
Peffers et al. and Wieringa.

Required sections:
1. Research approach and justification.
2. Actual iterative research process used in the project.
3. Functional requirements.
4. Non-functional requirements.
5. Local-first, privacy, copyright and deployment constraints.
6. Assumptions and non-goals.
7. Traceability from RQ1–RQ4 to artifact components and experiments.
8. Reason for separate RAG and MCP evaluation.
9. Ethical and reproducibility considerations.

Create:
- a design-science process diagram;
- functional and non-functional requirement tables;
- an RQ–artifact–experiment–evidence traceability matrix;
- a list of requirement evidence from supervisor/project documents.
```

---

## 5. Prompt for Chapter 4 — System Evolution and Design Decisions

```text
Using the master instruction, prepare Chapter 4:
System Evolution and Design Decisions.
Target length: 14–17 thesis pages.
This is the core learning-oriented chapter.

For every iteration use this exact structure:
1. Design tried.
2. Rationale.
3. Observation.
4. Project evidence.
5. Root cause.
6. Alternatives considered.
7. Selected correction and selection rationale.
8. Outcome.
9. Residual limitation.
10. Lesson learned.

Required evolution topics:
- initial monolithic dense-only RAG;
- dense retrieval limitations;
- BM25 + dense + RRF;
- duplicate passages and maximum-three-source rule;
- weak evidence, evidence grading and abstention;
- figure blindness and CLIP;
- local image paths and storage abstraction;
- procedural Blender and synthetic geometry;
- remote preview worker limitations;
- Z-Anatomy adoption;
- raw scene labels versus exportable_catalog.json;
- direct Python calls versus MCP stdio;
- fake 3D success versus model_url verification;
- Blender locking and cache;
- mixed architecture versus independent pipelines.

Do not state that a correction improved performance unless measured.
Where only qualitative evidence exists, label it as an observation.
Create a consolidated design-decision matrix and an evidence checklist.
```

---

## 6. Prompt for Chapter 5 — Final System Design and Implementation

```text
Using the master instruction, prepare Chapter 5:
Final System Design and Implementation.
Target length: 15–18 thesis pages.

Describe only the final frozen implementation. Avoid repeating the
historical narrative from Chapter 4.

Required sections:
1. Final system context and deployment topology.
2. Repository structure.
3. Next.js frontend and FastAPI API layer.
4. PDF ingestion, cleaning, chunking and metadata.
5. MiniLM, Chroma, BM25, RRF and final text retrieval.
6. Query processing, reranking, deduplication and evidence grading.
7. Answer synthesis, citations, abstention and grounding metadata.
8. CLIP image extraction, indexing, retrieval and late fusion.
9. Local/MinIO/Supabase storage and signed URLs.
10. MCP host and MCPBridge client.
11. FastMCP server and tool schemas.
12. exportable_catalog.json and structure resolution.
13. Blender export, GLB, annotations and Three.js.
14. Locking, caching, health checks and safe errors.
15. Configuration and reproducibility.

For every component, map the description to exact files/functions in
the frozen repository. Mark documentation–implementation differences
as [VERIFY RUNTIME WIRING].

Create:
- final architecture diagram;
- RAG and MCP sequence diagrams;
- component-to-code mapping table;
- exact environment/version table;
- API contract summary.
```

---

## 7. Prompt for Chapter 6 — Evaluation Methodology

```text
Using the master instruction, prepare Chapter 6: Evaluation Methodology.
Target length: 9–11 thesis pages.
Do not invent or prematurely discuss final results.

Required sections:
1. Evaluation objectives and RQ mapping.
2. Frozen repository, corpus, prompt, model and hardware configuration.
3. RAG evaluation dataset and question categories.
4. RAG baselines and controlled ablations.
5. Retrieval metrics: Precision@k, Recall@k, MRR and nDCG.
6. Generation metrics: correctness and completeness.
7. Grounding metrics: faithfulness, citation correctness,
   citation completeness and hallucination rate.
8. Boundary tests: unsupported, off-topic, typo and quotation cases.
9. Multimodal image evaluation.
10. MCP dataset: exact, natural-language, laterality, ambiguous,
    invalid, package and failure cases.
11. MCP metrics: catalog accuracy, tool use, export success,
    GLB validity, annotations, viewer, unverifiable-success rate,
    safe failure, cold latency and cached latency.
12. Human scoring rubric and disagreement handling.
13. Analysis plan and threats to validity.

Create empty, publication-ready result table templates.
Clearly label the existing spreadsheets as formative/exploratory unless
reproduced on the frozen final system.
```

---

## 8. Prompt for Chapter 7 — Results and Discussion

```text
Using the master instruction, prepare Chapter 7: Results and Discussion.
Target length: 13–16 thesis pages.

Use only measured evidence supplied in this chat/project.
Insert [FINAL VALUE REQUIRED] wherever data is missing.

Required sections:
1. Exact final tested configuration.
2. Dense-only versus hybrid retrieval results.
3. Query processing and deduplication findings.
4. Faithfulness, hallucination, citation and abstention findings.
5. Multimodal/CLIP figure results.
6. Exploratory versus final model-comparison findings.
7. MCP catalog-resolution and laterality results.
8. MCP tool, GLB, annotation and viewer results.
9. Cold versus cached latency.
10. Failure-case analysis.
11. Separate answers to RQ1–RQ4.
12. Comparison with prior literature.
13. Design trade-offs.
14. Threats to validity.

Use cautious wording:
- “The results suggest…”
- “Within the evaluated corpus…”
- “The prototype demonstrated…”

Do not use:
- “always”;
- “guarantees”;
- “clinically accurate”;
- “production-ready”.

Create a claim-to-result traceability table so that every conclusion
maps to an actual table, figure, screenshot or raw response.
```

---

## 9. Prompt for Chapter 8 — Conclusion and Future Work

```text
Using the master instruction, prepare Chapter 8:
Conclusion and Future Work.
Target length: 4–6 thesis pages.

Required sections:
1. Concise summary of problem and approach.
2. Evidence-based answers to RQ1–RQ4.
3. Contributions.
4. Technical and methodological limitations.
5. Future work ordered by priority.
6. Final reflection on the dual-pipeline design.

Include future work such as:
- OCR and layout-aware extraction;
- anatomy-specific embeddings or reranking;
- larger gold evaluation set;
- automated evaluation in CI;
- stronger claim-level citation verification;
- broader catalog testing;
- improved concurrency and cache invalidation;
- entity links between RAG answers and MCP models;
- student usability and learning-outcome studies;
- deployment hardening.

Do not introduce new experiments, references or numerical findings.
Do not overstate clinical or production readiness.
```

---

## 10. Prompt for a single subsection

```text
Draft Section [NUMBER AND TITLE] for Chapter [NUMBER].

Before drafting, provide:
1. The single argument this section must establish.
2. A list of claims in logical order.
3. Evidence required for each claim.
4. Scientific citations required for each theory claim.
5. Repository/evaluation evidence required for project claims.
6. Risks of overlap with other chapters.

Then write approximately [WORD COUNT] words of formal academic prose.
Use [EVIDENCE REQUIRED] and [REFERENCE REQUIRED] rather than guessing.
Finish with:
- a figure/table suggestion;
- a paragraph-transition suggestion;
- a claim-verification checklist.
```

---

## 11. Prompt for literature verification

```text
Audit the references used in this draft section.

For every citation:
- verify that the source exists;
- verify author names, year, title, venue, volume, pages and DOI;
- identify whether it is peer-reviewed, official documentation or a
  project source;
- confirm that the cited source actually supports the sentence;
- flag secondary citations where a primary source is preferable;
- flag claims requiring more than one source;
- output corrected BibTeX entries.

Do not create a reference when verification fails.
```

---

## 12. Prompt for claim and overstatement audit

```text
Audit this thesis section sentence by sentence.

Classify each substantive claim as:
A. scientific claim requiring literature;
B. implementation claim requiring code/project evidence;
C. result claim requiring measured data;
D. interpretation/inference;
E. common background statement.

For each claim, report:
- current evidence;
- missing evidence;
- whether the wording is too strong;
- a safer replacement sentence;
- the chapter in which the claim belongs.

Specifically flag claims involving:
- improvement;
- correctness;
- reliability;
- generalisation;
- educational effectiveness;
- medical accuracy;
- production readiness.
```

---

## 13. Prompt for final cross-chapter consistency

```text
Perform a complete thesis consistency audit.

Check:
- title, objectives and RQ wording are identical throughout;
- RAG and MCP are never mixed in evaluation;
- architecture names and endpoint names are consistent;
- baseline, exploratory and final-system results are separated;
- every numerical value has a source;
- every figure/table is referenced in the prose;
- no implementation detail contradicts the frozen repository;
- no literature claim lacks a verified citation;
- Chapter 4 explains why, while Chapter 5 explains how;
- Chapter 6 defines metrics before Chapter 7 reports them;
- Chapter 8 introduces no new results;
- terminology such as grounding, faithfulness, correctness,
  confidence and hallucination is used consistently;
- limitations are not hidden;
- the abstract matches the final results.

Return a prioritized correction list with page/section locations.
```

---

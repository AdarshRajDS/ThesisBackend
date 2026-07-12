# Thesis Evaluation Plan — Dual-Pipeline Architecture

**Document:** `evaluationThesis.md`  
**Project:** HFU Multimodal Anatomy Chatbot (`ThesisBackend`)  
**Scope:** Independent evaluation of the **RAG chatbot** and **MCP 3D anatomy system**, plus a small system-level assessment.

This document follows the thesis requirement that RAG is judged by **document grounding and citation quality**, while MCP is judged by **catalog resolution and verifiable 3D export**. The two pipelines must not be merged into a single score.

**Status legend**

| Label | Meaning |
| ----- | ------- |
| **Exploratory** | Early run on a non-frozen build; formative only — do not use for final thesis claims |
| **Final (planned)** | To be rerun on the frozen repository version with filled score columns |
| **Template** | Question defined; system answer and scores pending |

---

## Table of contents

1. [Evaluation philosophy](#1-evaluation-philosophy)
2. [RAG chatbot evaluation criteria](#2-rag-chatbot-evaluation-criteria)
3. [MCP 3D anatomy evaluation criteria](#3-mcp-3d-anatomy-evaluation-criteria)
4. [System-level criteria](#4-system-level-criteria)
5. [Recommended experimental comparisons](#5-recommended-experimental-comparisons)
6. [Manual scoring rubric (1–5)](#6-manual-scoring-rubric-15)
7. [Minimum evaluation datasets](#7-minimum-evaluation-datasets)
8. [Core criteria to prioritize](#8-core-criteria-to-prioritize)
9. [Professor question set (complete list)](#9-professor-evaluation-question-set-complete-list)
10. [Exploratory RAG results — cloud run (Q&A)](#10-exploratory-rag-results--cloud-run-qa)
11. [Local LM Studio experiment (Q&A)](#11-local-lm-studio-experiment-qa)
12. [Final RAG evaluation workbook (Q&A templates)](#12-final-rag-evaluation-workbook-qa-templates)
13. [MCP evaluation workbook (Q&A templates)](#13-mcp-evaluation-workbook-qa-templates)
14. [How to reproduce](#14-how-to-reproduce)

---

## 1. Evaluation philosophy

### Dual-pipeline separation

| Pipeline | User intent | Knowledge source | Primary success criterion |
| -------- | ----------- | ---------------- | ------------------------- |
| **RAG chatbot** | Answer textbook questions from uploaded PDFs | Hybrid BM25 + dense Chroma; optional CLIP figures | Grounded text, ≤3 citations, appropriate abstention |
| **MCP 3D anatomy** | Export and inspect a named body structure | Z-Anatomy `Startup.blend` + `exportable_catalog.json` | Verifiable GLB + annotation JSON + viewer load |

### Current production design (evaluation-relevant)

- **Retrieval:** Up to 32 hybrid candidates (`HybridRetriever`), deduplicated, reranked; final context limited to **three unique text passages** (plus optional multimodal excerpts).
- **Grounding:** Evidence grading and citation filter before generation; `allow_world_knowledge = false` blocks general-knowledge answers.
- **MCP integrity:** Success requires structured tool result with valid `model_url`; prompt-only export claims are treated as failure.
- **Catalog:** Geometry-validated `exportable_catalog.json` replaces raw label-index matching.

### Thesis reporting rule

Present **exploratory scores** (Section 9) as formative findings from project evolution. Reserve **final claims** for a reproducible run on the frozen implementation using Sections 10–11.

---

## 2. RAG chatbot evaluation criteria

### 2.1 Retrieval quality

These metrics evaluate whether the system retrieves the correct PDF passages **before** generating an answer.

| Criterion | What it measures | Suggested metric |
| --------- | ---------------- | ---------------- |
| Precision@k | How many retrieved passages are relevant | Relevant passages in top-k / k |
| Recall@k | Whether all expected evidence was retrieved | Retrieved relevant passages / all relevant passages |
| nDCG@k | Whether highly relevant passages appear near the top | Normalized discounted cumulative gain |
| MRR | Position of the first relevant passage | Mean reciprocal rank |
| Source hit rate | Whether the expected PDF/page appears in the results | Questions with correct source / all questions |
| Duplicate rate | Frequency of repeated passages or sources | Duplicate results / retrieved results |

**Thesis use:** Compare dense-only vs final hybrid BM25 + dense + RRF pipeline on the same frozen question set.

---

### 2.2 Answer quality

| Criterion | Evaluation question | Measurement |
| --------- | ------------------- | ----------- |
| Factual correctness | Is the answer anatomically correct according to the reference answer? | Human score, 1–5 |
| Answer relevance | Does the response directly answer the question? | Human score, 1–5 |
| Completeness | Does it include the important expected points? | Human score, 1–5 |
| Clarity | Is the answer understandable and appropriately structured? | Human score, 1–5 |
| Conciseness | Does it avoid unnecessary or unrelated content? | Human score, 1–5 |

Use a manually prepared gold answer or expected key points. **Do not** treat the LLM’s internal confidence score as evidence of medical correctness.

---

### 2.3 Grounding and faithfulness

| Criterion | Definition |
| --------- | ---------- |
| Claim support rate | Percentage of answer claims supported by at least one retrieved passage |
| Faithfulness score | Degree to which the answer is derived only from the supplied context |
| Hallucination rate | Unsupported factual claims divided by all factual claims |
| Unsupported answer rate | Questions where the system answered despite insufficient evidence |
| Grounded-answer rate | Answers whose main conclusions are supported by the retrieved evidence |

**Formulas:**

$$\text{Claim Support Rate} = \frac{\text{Supported factual claims}}{\text{All factual claims}}$$

$$\text{Hallucination Rate} = \frac{\text{Unsupported factual claims}}{\text{All factual claims}}$$

Earlier exploratory evaluation identified **unsupported generation under weak retrieval** as a major problem — this dimension is central to the thesis narrative.

---

### 2.4 Citation quality

| Criterion | What to verify |
| --------- | -------------- |
| Citation correctness | Does the cited passage actually support the preceding claim? |
| Citation completeness | Are all important factual claims cited? |
| Citation relevance | Is the cited source directly related to the answer? |
| Citation-source consistency | Does citation `[1]` correspond to source card 1? |
| Citation location accuracy | Is the reported PDF name and page correct? |
| Citation redundancy | Are duplicate sources unnecessarily shown? |

**Formulas:**

$$\text{Citation Correctness} = \frac{\text{Correct supporting citations}}{\text{All citations}}$$

$$\text{Citation Completeness} = \frac{\text{Claims requiring citations that are cited}}{\text{All claims requiring citations}}$$

Evaluate the **maximum-three-reference rule** for quality, not quantity: three highly relevant sources beat many weak or duplicated references.

---

### 2.5 Abstention and boundary handling

Test whether the system refuses appropriately when evidence is unavailable.

**Include:**

- Unsupported anatomy questions (topic not in corpus).
- Questions outside uploaded documents.
- General-knowledge questions with `allow_world_knowledge = false`.
- Questions asking for exact quotations not present in the corpus.
- Off-topic questions.
- Questions with intentionally misleading assumptions.

| Metric | Definition |
| ------ | ---------- |
| Correct abstention rate | Unsupported questions correctly refused / all unsupported questions |
| False abstention rate | Supported questions incorrectly refused / all supported questions |
| Unsafe answer rate | Unsupported questions answered confidently / all unsupported questions |
| Consent compliance | World knowledge used only when permission was given |

Exploratory runs showed **strong boundary handling** but weaknesses in **exact-quote verification** and **external references**.

---

### 2.6 Multimodal image evaluation

For figure-related questions, evaluate image retrieval separately from text retrieval.

| Criterion | Description |
| --------- | ----------- |
| Figure retrieval success | At least one relevant figure appears |
| Image relevance@k | Relevant images among the top-k returned images |
| Image-question alignment | The image depicts the structure or concept requested |
| Image-answer consistency | The image does not contradict the textual answer |
| Image diversity | Returned images are not duplicates |
| URL availability | Image URL loads successfully |
| Metadata correctness | Image is associated with the correct PDF/page |

$$\text{Figure Retrieval Success Rate} = \frac{\text{Figure questions with at least one relevant image}}{\text{All figure-related questions}}$$

**Ablations to compare:** text-only retrieval · multimodal CLIP retrieval · fused text + image retrieval.

---

### 2.7 Robustness tests

Include variations of the same question:

- Correct spelling vs typographical error.
- Abbreviation vs full anatomical term.
- English common name vs Latin/catalog terminology.
- Short vs complex question.
- Singular vs plural.
- Left vs right anatomy.
- Explicit figure request vs implicit visual question.

**Possible metrics:** typo recovery rate · paraphrase consistency · laterality correctness · answer stability across equivalent queries.

---

## 3. MCP 3D anatomy evaluation criteria

The MCP evaluation determines whether a natural-language structure request produces the **correct, verifiable, and usable 3D artifact**.

### 3.1 Catalog resolution accuracy

| Criterion | Description |
| --------- | ----------- |
| Exact-label accuracy | Correctly resolves entries such as `Femur.l` |
| Natural-language accuracy | Correctly resolves “left femur” |
| Laterality accuracy | Distinguishes left and right structures |
| Synonym resolution | Maps common names to catalog labels |
| Ambiguity detection | Requests clarification instead of choosing arbitrarily |
| Invalid-query rejection | Rejects unsupported or malformed inputs safely |

$$\text{Catalog Match Accuracy} = \frac{\text{Queries resolved to the correct catalog entry}}{\text{All valid catalog queries}}$$

**Test-set strata:**

1. Exact catalog labels  
2. Natural-language structure names  
3. Left/right structures  
4. Synonyms  
5. Ambiguous structures  
6. Invalid or nonexistent structures  

The final system uses geometry-validated `exportable_catalog.json` because raw label matching could find a name without proving exportable geometry existed.

---

### 3.2 MCP tool-execution integrity

Verify the system genuinely executed MCP tools rather than merely generating a success statement.

**Checklist:**

- [ ] `mcp_tools_used` contains `search_anatomy_catalog`
- [ ] An export tool was called
- [ ] A structured result was returned
- [ ] `model_url` is present before success is reported
- [ ] No viewer is displayed when export fails
- [ ] Tool failures are exposed as explicit error states

$$\text{Verified Tool Execution Rate} = \frac{\text{Successful responses with valid export tool evidence}}{\text{Responses claiming successful export}}$$

Target for the final implementation: **100%** — success without a valid model URL is failure.

---

### 3.3 Export success and artifact completeness

| Criterion | Pass condition |
| --------- | -------------- |
| Export success | Tool returns `status = ok` |
| GLB generation | GLB file exists and has non-zero size |
| GLB accessibility | `model_url` returns HTTP 200 |
| Annotation generation | Annotation JSON exists |
| Viewer generation | `viewer_url` is returned |
| Viewer loading | Three.js viewer loads without error |
| Mesh visibility | Requested structure is visible |
| Correct structure | Exported mesh corresponds to the requested anatomy |
| Package completeness | Required subparts are present for package exports |

$$\text{Export Success Rate} = \frac{\text{Valid GLB exports}}{\text{Valid export requests}}$$

Report separate rates for: exact-label · natural-language · single-part · package · cached · new exports.

---

### 3.4 Annotation evaluation

| Criterion | Description |
| --------- | ----------- |
| Annotation file validity | JSON is syntactically valid |
| Annotation coverage | Expected anatomical labels are present |
| Label correctness | Labels correspond to the exported structure |
| Anchor correctness | Labels appear near the intended structure |
| Viewer consistency | Viewer labels match annotation JSON |
| Duplicate-label rate | Repeated or meaningless labels are limited |

Assess annotation correctness manually on a subset using the 1–5 rubric (Section 6).

---

### 3.5 Latency and caching

| Measurement | Start and end point |
| ----------- | ------------------- |
| Catalog-search latency | Query received → match returned |
| Cold-export latency | Export request → new GLB availability |
| Cached-export latency | Repeated request → URL return |
| Viewer-load latency | Viewer request → visible model |
| End-to-end latency | User submits request → rendered viewer |

$$\text{Cache Speed-up} = \frac{\text{Mean cold-export latency}}{\text{Mean cached-export latency}}$$

Report median and percentile values; Blender export times may contain large outliers.

---

### 3.6 MCP failure-handling evaluation

**Test cases (minimum):**

- Vague query: “show me the organ”
- Ambiguous query: “kidney”
- Nonexistent structure
- Invalid characters or very long input
- Missing Blender executable
- Missing `Startup.blend`
- Missing catalog
- Blender timeout / subprocess failure
- Missing generated GLB
- Invalid viewer URL
- Concurrent requests

**Pass conditions:** meaningful error · no false success · no empty viewer · clarification/suggestions where appropriate · backend remains operational.

---

## 4. System-level criteria

These apply to both pipelines but **do not replace** separate technical evaluations.

| Category | Possible criteria |
| -------- | ----------------- |
| Usability | Ease of asking questions, understanding citations, opening the 3D viewer |
| Learnability | Whether first-time users understand the two modes |
| Reliability | Repeated requests produce stable results |
| Reproducibility | System installs from documented environment |
| Modularity | RAG and MCP can fail independently |
| Transparency | Sources, tools, and errors are visible |
| Local-first compliance | Sensitive PDFs and anatomy assets stay in intended environment |
| Performance | Response latency and resource usage |
| Accessibility | Labels, language support, interface readability |
| Educational usefulness | Answers and visualizations help users understand anatomy |

**Optional user study (Likert 1–5):**

- The answer was understandable.
- The references were useful.
- The retrieved images supported understanding.
- The 3D model represented the requested structure.
- The viewer was easy to operate.
- The distinction between document Q&A and 3D mode was clear.

This is a **usability and educational-feasibility assessment**, not clinical validation.

---

## 5. Recommended experimental comparisons

### RAG ablations

| Experiment | Comparison |
| ---------- | ---------- |
| Retrieval | Dense-only vs hybrid BM25+dense |
| Figures | Text-only vs multimodal |
| Grounding | With vs without evidence grading |
| Deduplication | With vs without source deduplication |
| Context size | Different candidate and final-passage limits |
| Models | Qwen vs Gemma vs selected final model |
| Boundary handling | Consent disabled vs enabled |

### MCP ablations

| Experiment | Comparison |
| ---------- | ---------- |
| Resolver | Raw label index vs exportable catalog |
| Execution | Prompt-only claim vs MCP-verified tool execution |
| Query form | Exact label vs natural language |
| Export type | Single-part vs package |
| Performance | Cold export vs cache hit |
| Orchestration | Fast path vs LLM tool loop |

These comparisons support the thesis narrative that the system evolved through observed problems rather than as a single static design.

---

## 6. Manual scoring rubric (1–5)

| Score | Interpretation |
| ----: | -------------- |
| 5 | Fully correct, relevant, supported, and complete |
| 4 | Mostly correct; only minor omission or imprecision |
| 3 | Partly correct but with noticeable omissions or weak evidence |
| 2 | Major inaccuracies, irrelevant evidence, or unsupported claims |
| 1 | Incorrect, ungrounded, or failed response |

Apply separately to: **accuracy · completeness · relevance · grounding · citation quality · boundary handling**.

---

## 7. Minimum evaluation datasets

### RAG dataset (~55 questions)

| Category | Count |
| -------- | ----: |
| Direct factual questions | 15 |
| Complex or multi-step questions | 10 |
| Figure-related questions | 10 |
| Exact-quotation questions | 5 |
| Unsupported or off-topic questions | 10 |
| Typo or paraphrase variants | 5 |
| **Total** | **~55** |

### MCP dataset (~50 queries)

| Category | Count |
| -------- | ----: |
| Exact catalog labels | 10 |
| Natural-language names | 10 |
| Left/right structures | 10 |
| Synonyms | 5 |
| Ambiguous terms | 5 |
| Invalid or nonexistent structures | 5 |
| Repeated requests (caching tests) | 5 |
| **Total** | **~50** |

Sample sizes are recommendations, not mandatory statistical requirements.

---

## 8. Core criteria to prioritize

When thesis time is limited, prioritize these **twelve**:

### RAG

1. Recall@k  
2. nDCG@k  
3. Answer correctness  
4. Claim support rate  
5. Hallucination rate  
6. Citation correctness  
7. Correct abstention rate  
8. Figure retrieval success rate  

### MCP

9. Catalog match accuracy  
10. Verified export success rate  
11. Viewer-load success rate  
12. Median cold and cached latency  

---

## 9. Professor evaluation question set (complete list)

Nine German anatomy questions from the professor, used in both the exploratory (§10) and local LM Studio (§11) runs.

| # | ID (cloud) | ID (LM Studio) | Category | Question |
| -: | ---------- | -------------- | -------- | -------- |
| 1 | EXP-R01 | LM-R01 | Complex / multi-step | Bitte stelle mir die wichtigsten Muskeln für die Bewegung der Sprunggelenke zusammen und sortiere diese bitte nach Bewegungsrichtungen. |
| 2 | EXP-R02 | LM-R02 | Complex + figures | Bitte stelle mir eine Übersicht über die wichtigen Muskeln zusammen, welche benötigt werden, um eine Faust zu schließen. Hierbei sollte die Innervation berücksichtigt werden. Bitte zeige mir dazu auch zwei didaktisch gute Bilder. |
| 3 | EXP-R03 | LM-R03 | Clinical anatomy | Welche Faktoren begünstigen einen Hochstand des Humeruskopfes und damit eine Enge unter dem Schulterdach? |
| 4 | EXP-R04 | LM-R04 | Direct factual | Welcher Muskel ist der wichtigste Hüftbeuger beim Menschen? |
| 5 | EXP-R05 | LM-R05 | Direct factual + figures | Kannst Du mir kurz erklären, wie der Vestibulo-Okuläre-Reflex funktioniert? |
| 6 | EXP-R06 | LM-R06 | Boundary | Gibt es den Vestibulookulären Reflex nur in der Horizontalen? |
| 7 | EXP-R07 | LM-R07 | Direct factual | Welche Augenmuskeln wirken denn mit welchen Borgengängen zusammen? |
| 8 | EXP-R08 | LM-R08 | Direct factual | Bitte erkläre mir die Funktion des Herzens. |
| 9 | EXP-R09 | LM-R09 | Complex / synthesis | Bitte erstelle mir ein Kurzreferat für 3 Minuten für den Schultergürtel wo es um Bewegungen des Armes geht und Dinge wie Abduktion und Elevation. |

**Run commands**

```powershell
# Cloud / first run (historical)
python scripts/run_german_eval.py german_eval_results.json

# Local LM Studio experiment
python scripts/run_german_eval.py german_eval_lmstudio_results.json
python scripts/retry_failed_eval.py german_eval_lmstudio_results.json
```powershell
python scripts/refresh_eval_md.py
```
```

---

## 10. Exploratory RAG results — cloud run (Q&A)

**Source file:** `german_eval_results.json`  
**Run date:** June 2026 (formative)  
**LLM at run time:** cloud Groq (historical)  
**Endpoint:** `POST /rag/ask`  
**Status:** Exploratory — compare with §11 local LM Studio run

### 10.0 Summary

| ID | Outcome | Sources | Images |
| -- | ------- | ------- | ------ |
| EXP-R01 | Abstained | 3 | 0 |
| EXP-R02 | Error | — | — |
| EXP-R03 | Abstained | 3 | 0 |
| EXP-R04 | Abstained | 3 | 0 |
| EXP-R05 | Answered | 3 | 2 |
| EXP-R06 | Answered | 3 | 3 |
| EXP-R07 | Answered | 3 | 0 |
| EXP-R08 | Abstained | 3 | 0 |
| EXP-R09 | Answered | 3 | 0 |

---

### EXP-R01 — Bitte stelle mir die wichtigsten Muskeln für die Bewegung der Sprungge…

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R01 |
| **Category** | Complex / multi-step |
| **Language** | German |

**Question:**  
Bitte stelle mir die wichtigsten Muskeln für die Bewegung der Sprunggelenke zusammen und sortiere diese bitte nach Bewegungsrichtungen.

**Expected key points (gold):**  
Peroneus longus/brevis, tibialis anterior/posterior, gastrocnemius/soleus, grouped by movement directions.

**System answer:**  
Die bereitgestellten Textpassagen enthalten keine Informationen über die Muskeln, die für die Bewegung der Sprunggelenke zuständig sind. Daher kann ich Ihre Frage anhand des Kontextes nicht beantworten.

**Sources retrieved:**  
1. **anatomy+phys+vol2a.pdf** p.288 — All formed elements arise from stem cells of the red bone marrow. Recall that stem cells undergo mitosis plus cytokinesis (cellular division) to give rise to new daughter cells: One of these remains a stem cell and the other differentiates into one of any number of diverse cell t…
2. **anatomy+phys+vol2a.pdf** p.537 — temporomandibular joint (TMJ), 351, 370 tendinous intersections, 435, 463 tendon, 337, 370 tendon sheath, 338, 370 tenia coli, 1075 teniae coli, 1053 tensor fascia lata, 450, 463 teres major, 442, 463 teres minor, 442, 463 INDEX 1331
3. **anatomy+phys+vol2a.pdf** p.60 — the developmental pattern, it is possible to learn what the major regions of the nervous system are. The Neural Tube To begin, a sperm cell and an egg cell fuse to become a fertilized egg. The fertilized egg cell, or zygote, starts dividing to generate the cells that make up an e…

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 3
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### EXP-R02 — Bitte stelle mir eine Übersicht über die wichtigen Muskeln zusammen, w…

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R02 |
| **Category** | Complex + figure request |
| **Language** | German |

**Question:**  
Bitte stelle mir eine Übersicht über die wichtigen Muskeln zusammen, welche benötigt werden, um eine Faust zu schließen. Hierbei sollte die Innervation berücksichtigt werden. Bitte zeige mir dazu auch zwei didaktisch gute Bilder.

**Expected key points (gold):**  
Flexor digitorum superficialis/profundus, flexor pollicis longus, lumbricals; median/ulnar innervation; 2 figures.

**System answer:**  
`HTTP Error 500: Internal Server Error`

---
### EXP-R03 — Welche Faktoren begünstigen einen Hochstand des Humeruskopfes und dami…

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R03 |
| **Category** | Direct factual / clinical anatomy |
| **Language** | German |

**Question:**  
Welche Faktoren begünstigen einen Hochstand des Humeruskopfes und damit eine Enge unter dem Schulterdach?

**Expected key points (gold):**  
Humeral head high-riding: rotator cuff weakness, capsular tightness; subacromial impingement.

**System answer:**  
Die bereitgestellten Textpassagen enthalten keine Informationen, die die Faktoren für einen Hochstand des Humeruskopfes oder eine Enge unter dem Schulterdach beschreiben.

**Sources retrieved:**  
1. **anatomy+phys+vol2a.pdf** p.536 — shaft of the humerus, 292, 322 shaft of the radius, 294, 322 shaft of the tibia, 310, 322 shaft of the ulna, 294, 322 short bone, 208, 234 short reflex, 624, 641 short-term memory, 654, 679 shunt, 1257, 1283 sickle cell disease, 751, 771 sigmoid colon, 1051, 1074 sigmoid sinuses,…
2. **anatomy+phys+vol2a.pdf** p.530 — meatuses, 975 Mechanical digestion, 1029 mechanical digestion, 1073 mechanically gated channel, 489, 504 mechanoreceptor, 563, 602 meconium, 1258, 1282 Medial, 31 medial, 39 medial (internal) rotation, 348, 368 medial border of the scapula, 291, 320 medial compartment of the thig…
3. **anatomy+phys+vol2a.pdf** p.198 — anatomical underpinnings. The German neurologist and histologist Korbinian Brodmann, who made a careful study of the cytoarchitecture of the cerebrum around the turn of the nineteenth century, described approximately 50 regions of the cortex that differed enough from each other t…

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 3
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### EXP-R04 — Welcher Muskel ist der wichtigste Hüftbeuger beim Menschen?

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R04 |
| **Category** | Direct factual |
| **Language** | German |

**Question:**  
Welcher Muskel ist der wichtigste Hüftbeuger beim Menschen?

**Expected key points (gold):**  
Iliopsoas (iliacus + psoas major) as primary hip flexor.

**System answer:**  
Der bereitgestellte Kontext enthält keine Informationen über die Muskelanatomie oder welche Muskeln als wichtigste Hüftbeuger beim Menschen gelten.

**Sources retrieved:**  
1. **anatomy+phys+vol2a.pdf** p.198 — anatomical underpinnings. The German neurologist and histologist Korbinian Brodmann, who made a careful study of the cytoarchitecture of the cerebrum around the turn of the nineteenth century, described approximately 50 regions of the cortex that differed enough from each other t…
2. **anatomy+phys+vol2a.pdf** p.68 — Figure 13.7 Lobes of the Cerebral Cortex The cerebral cortex is divided into four lobes. Extensive folding increases the surface area available for cerebral functions. Different regions of the cerebral cortex can be associated with particular functions, a concept known as localiz…
3. **anatomy+phys+vol2a.pdf** p.20 — the blood. Response. The nervous system produces a response on the basis of the stimuli perceived by sensory structures. An obvious response would be the movement of muscles, such as withdrawing a hand from a hot stove, but there are broader uses of the term. The nervous system c…

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 3
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### EXP-R05 — Kannst Du mir kurz erklären, wie der Vestibulo-Okuläre-Reflex funktion…

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R05 |
| **Category** | Direct factual + implicit figure |
| **Language** | German |

**Question:**  
Kannst Du mir kurz erklären, wie der Vestibulo-Okuläre-Reflex funktioniert?

**Expected key points (gold):**  
Vestibular nuclei → ocular motor nuclei; stabilizes retinal image during head movement.

**System answer:**  
Der vestibululo-okuläre Reflex (VOR) ist ein Mechanismus, der dazu dient, Bilder auf der Netzhaut zu stabilisieren, während der Kopf und der Körper sich bewegen.

**Funktionsweise:**

1. **Verbindung:** Fasern der vestibulären Kerne projizieren zu den Nuclei des Okulomotorius, Trochlearis und Abducens, um Signale entlang der Hirnnerven zu beeinflussen. Diese Verbindungen bilden den Weg des VOR.
2. **Ziel:** Der Reflex kompensiert die Bewegung des Kopfes und des Körpers.
3. **Ergebnis:** Er stabilisiert die Bilder auf der Netzhaut, sodass die Augen auch bei Kopfbewegungen auf einem visuellen Reiz zentriert bleiben.

Kurz gesagt: Der VOR sorgt dafür, dass die Augen den visuellen Reiz stabilisieren, selbst wenn sich der Kopf bewegt.

**Sources retrieved:**  
1. **anatomy+phys+vol2a.pdf** p.131 — To assist the visual system, fibers of the vestibular nuclei project to the oculomotor, trochlear, and abducens nuclei to influence signals sent along the cranial nerves. These connections constitute the pathway of the vestibulo-ocular reflex (VOR), which compensates for head and…
2. **anatomy+phys+vol2a.pdf** p.152 — vestibulo-ocular reflex (VOR) vestibulospinal tract visceral sense vision visual acuity vitreous humor working memory zonule fibers reflex based on connections between the vestibular system and the cranial nerves of eye movements that ensures images are stabilized on the retina a…
3. **anatomy+phys+vol2a.pdf** p.213 — particular stimuli to each receptive organ. General senses can be tested through sensory discrimination of touch versus painful stimuli. The oculomotor, trochlear, and abducens nerves control the extraocular muscles and are connected by the medial longitudinal fasciculus to coord…

**Images:**  
**Count:** 2
1. `http://localhost:9000/anatomy-images/anatomy%2Bphys%2Bvol2a/page_169/anatomy%2Bphys%2Bvol2a_page_169_img_0.jpeg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20260628%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260628T075950Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=4c70a43ae89f4c29c31a840a71399577874a06a9d65dd64fc9899043786bffb6` (page 169)
2. `http://localhost:9000/anatomy-images/anatomy%2Bphys%2Bvol2a/page_167/anatomy%2Bphys%2Bvol2a_page_167_img_1.jpeg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20260628%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260628T075950Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=950d9621cfe5511c3fb435db7dc75201c15384bcd5a0c3701a6fedd69dd317b8` (page 167)

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 3
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### EXP-R06 — Gibt es den Vestibulookulären Reflex nur in der Horizontalen?

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R06 |
| **Category** | Complex / boundary |
| **Language** | German |

**Question:**  
Gibt es den Vestibulookulären Reflex nur in der Horizontalen?

**Expected key points (gold):**  
Semicircular canals: horizontal + vertical planes; VOR not limited to horizontal.

**System answer:**  
Der Kontext beschreibt die Orientierung der halbkreisförmigen Kanäle (semicircular canals), die Erweiterungen des Vestibulus sind:

"Die halbkreisförmigen Kanäle sind drei ringförmige Erweiterungen des Vestibulus. Eine ist in der horizontalen Ebene ausgerichtet, während die anderen beiden in der vertikalen Ebene ausgerichtet sind."

Der Kontext liefert keine Aussage darüber, ob der vestibulookuläre Reflex (VOR) *nur* in der Horizontalen existiert; er beschreibt lediglich die räumliche Ausrichtung der Vestibularstrukturen.

**Sources retrieved:**  
1. **anatomy+phys+vol2a.pdf** p.152 — vestibulo-ocular reflex (VOR) vestibulospinal tract visceral sense vision visual acuity vitreous humor working memory zonule fibers reflex based on connections between the vestibular system and the cranial nerves of eye movements that ensures images are stabilized on the retina a…
2. **anatomy+phys+vol2a.pdf** p.226 — vestibulo-ocular reflex (VOR) vestibulocerebellum Weber test Wernicke’s area reflex based on connections between the vestibular system and the cranial nerves of eye movements that ensures that images are stabilized on the retina as the head and body move flocculonodular lobe of t…
3. **anatomy+phys+vol2a.pdf** p.119 — Figure 14.11 Linear Acceleration Coding by Maculae The maculae are specialized for sensing linear acceleration, such as when gravity acts on the tilting head, or if the head starts moving in a straight line. The difference in inertia between the hair cell stereocilia and the otol…

**Images:**  
**Count:** 3
1. `http://localhost:9000/anatomy-images/anatomy%2Bphys%2Bvol2a/page_22/anatomy%2Bphys%2Bvol2a_page_22_img_1.jpeg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20260628%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260628T080128Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=66a6d6d80cd86087c8e1a8e62b0172d5091f2001ff7f506cdb433d0bf6fd34dc` (page 22)
2. `http://localhost:9000/anatomy-images/anatomy%2Bphys%2Bvol2a-30-60/page_7/anatomy%2Bphys%2Bvol2a-30-60_page_7_img_1.jpeg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20260628%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260628T080128Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=6d934265a05843305f841e04969ba59f133e507c1934e918cf31b20e9825978a` (page 7)
3. `http://localhost:9000/anatomy-images/anatomy%2Bphys%2Bvol2a/page_36/anatomy%2Bphys%2Bvol2a_page_36_img_1.jpeg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=minioadmin%2F20260628%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260628T080128Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=c5cabaa1da8edff901be91e7b879450a3a9e8d061757d8aec3efd56df38f8817` (page 36)

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 3
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### EXP-R07 — Welche Augenmuskeln wirken denn mit welchen Borgengängen zusammen?

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R07 |
| **Category** | Direct factual |
| **Language** | German |

**Question:**  
Welche Augenmuskeln wirken denn mit welchen Borgengängen zusammen?

**Expected key points (gold):**  
Extraocular muscle ↔ semicircular canal pairings.

**System answer:**  
Die extraokularen Muskeln werden von drei Hirnnerven innerviert.

*   Der **laterale Rectus** (verursacht Abduktion des Auges) wird vom **Abducensnerv** innerviert.
*   Der **oblique Superior** wird vom **Trochlearnerv** innerviert.

**Sources retrieved:**  
1. **anatomy+phys+vol2a.pdf** p.121 — compensate for the superior rectus pulling at approximately a 20-degree angle, rather than straight up. The same is true for the inferior rectus, which is compensated by contraction of the inferior oblique. A seventh muscle in the orbit is the levator palpebrae superioris, which …
2. **anatomy+phys+vol2a.pdf** p.68 — Figure 13.7 Lobes of the Cerebral Cortex The cerebral cortex is divided into four lobes. Extensive folding increases the surface area available for cerebral functions. Different regions of the cerebral cortex can be associated with particular functions, a concept known as localiz…
3. **anatomy+phys+vol2a.pdf** p.5 — 10.8 Smooth Muscle  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . 402 10.9 Development and Regeneration of Muscle Tissue .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . 405 Chapter 11: The Muscular System …

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 3
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### EXP-R08 — Bitte erkläre mir die Funktion des Herzens.

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R08 |
| **Category** | Direct factual |
| **Language** | German |

**Question:**  
Bitte erkläre mir die Funktion des Herzens.

**Expected key points (gold):**  
Heart pump function, chambers, systemic/pulmonary circulation.

**System answer:**  
Die bereitgestellten Textpassagen enthalten keine Informationen über die Funktion des Herzens.

**Sources retrieved:**  
1. **anatomy+phys+vol2a.pdf** p.110 — is most important to autonomic functions. A special sense is one that has a specific organ devoted to it, namely the eye, inner ear, tongue, or nose. Each of the senses is referred to as a sensory modality. Modality refers to the way that information is encoded, which is similar …
2. **anatomy+phys+vol2a.pdf** p.20 — combines sensory perceptions and higher cognitive functions such as memories, learning, and emotion to produce a response. Sensation. The first major function of the nervous system is sensation—receiving information about the environment to gain input about what is happening outs…
3. **anatomy+phys+vol2a.pdf** p.198 — on the outside of the cerebrum. It is approximately a millimeter thick in most regions and highly folded to fit within the limited space of the cranial vault. These higher functions are distributed across various regions of the cortex, and specific locations can be said to be res…

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 3
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### EXP-R09 — Bitte erstelle mir ein Kurzreferat für 3 Minuten für den Schultergürte…

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R09 |
| **Category** | Complex / synthesis |
| **Language** | German |

**Question:**  
Bitte erstelle mir ein Kurzreferat für 3 Minuten für den Schultergürtel wo es um Bewegungen des Armes geht und Dinge wie Abduktion und Elevation.

**Expected key points (gold):**  
Shoulder girdle, abduction/elevation, scapulohumeral rhythm, relevant muscles.

**System answer:**  
Basierend auf den bereitgestellten Textpassagen kann ich Ihnen ein Kurzreferat über die motorische Steuerung von Armbewegungen und die damit verbundenen Mechanismen erstellen.

Da der Kontext sich primär auf die neurologische Kontrolle von Bewegung (Propriozeption, Reflexe) und Augenmuskeln konzentriert, liegt der Fokus des Referats auf dem Zusammenspiel von Gehirn und Muskeln bei der Bewegung des Arms.

***

## Kurzreferat: Motorische Steuerung von Armbewegungen und Propriozeption (ca. 3 Minuten)

**Einleitung: Die motorische Kontrolle des Arms**

Wir beginnen mit der Betrachtung, wie unser Körper Bewegungen ausführt und korrigiert. Die Bewegung des Arms ist ein komplexer motorischer Prozess, der nicht nur durch direkte Befehle, sondern auch durch kontinuierliches Feedback gesteuert wird.

**1. Propriozeptives Feedback und Korrekturmechanismen**

Wenn wir den Arm bewegen, geschieht dies als ein fortlaufender motorischer Prozess. Um die Bewegung präzise zu steuern, nutzt das Gehirn eine wichtige Rückmeldung: das **propriozeptive Feedback**. Dieses Feedback informiert das zentrale Nervensystem über die aktuelle Position und den Zustand der Gliedmaßen.

*   **Die Rolle des Kleinhirns (Cerebellum):** Das Kleinhirn spielt eine entscheidende Rolle bei der Koordination. Es vergleicht den motorischen Befehl, der vom Gehirn gesendet wird, mit dem propriozeptiven Feedback. Wenn eine Diskrepanz auftritt, passt das Kleinhirn die absteigenden Signale an, um die Bewegung zu korrigieren und die ursprüngliche Position wiederherzustellen.
*   **Muskuläre Reaktion:** Um diese Korrektur zu ermöglichen, senden Strukturen wie der **Rote Nucleus** zusätzliche Signale an die peripheren Nerven (LMN), damit die Armmuskeln kurzzeitig eine erhöhte Kontraktion ausführen können, um die veränderte Position zu überwinden und die Ausgangsposition wiederzuerlangen.

**2. Reflexe und Muskelkontrolle**

Die Kontrolle der Muskelkontraktion wird durch Reflexe unterstützt. Beispielsweise ist der **Check-Reflex** abhängig von der Eingabe des Kleinhirns, um sicherzustellen, dass die erhöhte Kontraktion nicht weiter fortgesetzt wird, nachdem eine Widerstandslosigkeit aufgehoben wurde. Dies gewährleistet eine kontrollierte und sichere Bewegung.

**Zusammenfassung:**

Die Bewegungen des Arms – wie Abduktion oder Elevation – werden durch ein dynamisches Zusammenspiel von motorischen Befehlen, sensorischem Feedback (Propriozeption) und Korrekturmechanismen im Kleinhirn gesteuert. Dieses System stellt sicher, dass die Bewegung nicht nur ausgeführt wird, sondern auch präzise und kontrolliert bleibt.

***
*(Hinweis: Die bereitgestellten Textpassagen fokussieren stark auf die neurologische Steuerung von Bewegungen und Reflexe. Für eine vollständige anatomische Darstellung des Schultergürtels (Bänder, Knochen) müssten weitere anatomische Texte herangezogen werden.)*

**Sources retrieved:**  
1. **anatomy+phys+vol2a.pdf** p.220 — position. The extension of the arms is an ongoing motor process, and the tap or push on the arms presents a change in the proprioceptive feedback. The cerebellum compares the cerebral motor command with the proprioceptive feedback and adjusts the descending input to correct. The …
2. **anatomy+phys+vol2a.pdf** p.121 — compensate for the superior rectus pulling at approximately a 20-degree angle, rather than straight up. The same is true for the inferior rectus, which is compensated by contraction of the inferior oblique. A seventh muscle in the orbit is the levator palpebrae superioris, which …
3. **anatomy+phys+vol2a.pdf** p.4 — Chapter 8: The Appendicular Skeleton .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . 287 8.1 The Pectoral Girdle  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .  . 288 8.2 Bones of t…

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 3
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---


## 11. Local LM Studio experiment (Q&A)

**Source file:** `german_eval_lmstudio_results.json`  
**Run date:** 12 July 2026 (900 s retry completed)  
**LLM provider:** LM Studio (`LLM_PROVIDER=lmstudio`, local-only enforced)  
**API base:** http://127.0.0.1:1234/v1  
**Configured model:** `google/gemma-4-e2b`  
**Models loaded (observed):** `qwen3.5-9b-deepseek-v4-flash`, `biomistral-7b`  
**Endpoint:** `POST /rag/ask` with `language=de`  
**Outcome:** 7/9 answered · 1 HTTP 500 (LM-R02) · 1 timeout (LM-R09)  
**Thesis note:** Several answers fall back to general anatomy when retrieval is weak (grounding / consent risk).

### 11.0 Summary

| ID | Outcome | Sources | Images |
| -- | ------- | ------- | ------ |
| LM-R01 | Answered (world knowledge) | 5 | 0 |
| LM-R02 | Error | — | — |
| LM-R03 | Answered (world knowledge) | 5 | 0 |
| LM-R04 | Answered | 5 | 0 |
| LM-R05 | Answered | 5 | 2 |
| LM-R06 | Answered | 4 | 3 |
| LM-R07 | Answered (world knowledge) | 4 | 0 |
| LM-R08 | Answered | 4 | 0 |
| LM-R09 | Error | — | — |

### 11.0.1 Cloud vs local comparison (same professor set)

| ID | Cloud run (§10) | LM Studio (§11) | Thesis note |
| -- | --------------- | --------------- | ----------- |
| EXP-R01 | Abstained | Answered (world knowledge) | Local answered with world knowledge; cloud abstained |
| EXP-R02 | Error | Error | Both failed (500) |
| EXP-R03 | Abstained | Answered (world knowledge) | Local world-knowledge fill; cloud abstained |
| EXP-R04 | Abstained | Answered | Local grounded answer (iliopsoas); cloud abstained |
| EXP-R05 | Answered | Answered | Both answered VOR; local added images |
| EXP-R06 | Answered | Answered | Both answered; local added images |
| EXP-R07 | Answered | Answered (world knowledge) | Local world knowledge; cloud partial |
| EXP-R08 | Abstained | Answered | Local corpus-grounded heart; cloud abstained |
| EXP-R09 | Answered | Error | Cloud off-topic answer; local timeout |

---
---

### LM-R01 — Bitte stelle mir die wichtigsten Muskeln für die Bewegung der Sprungge…

| Field | Content |
| ----- | ------- |
| **ID** | LM-R01 |
| **Category** | Complex / multi-step |
| **Language** | German |

**Question:**  
Bitte stelle mir die wichtigsten Muskeln für die Bewegung der Sprunggelenke zusammen und sortiere diese bitte nach Bewegungsrichtungen.

**Expected key points (gold):**  
Peroneus longus/brevis, tibialis anterior/posterior, gastrocnemius/soleus, grouped by movement directions.

**System answer:**  
Die bereitgestellten Textpassagen enthalten keine Informationen über die Muskulatur des Sprunggelenks. Daher werde ich auf allgemeine anatomische Kenntnisse zurückgreifen, um die wichtigsten Muskeln für die Bewegung der Sprunggelenke zusammenzustellen und nach Bewegungsrichtungen zu sortieren.

**Wichtige Muskeln des Sprunggelenks (Ankergelenk) nach Bewegungsrichtung:**

1. **Dorsalflexion** (Zurückziehen des Fußes Richtung Schienbein):
   - *Tibialis anterior* (Hauptmuskulatur)
   - *Extensor hallucis longus*
   - *Extensor digitorum longus*
   - *Peroneus tertius* (oft als Teil der Extensoren betrachtet)

2. **Plantarflektion** (Absenken des Fußes Richtung Boden):
   - *Gastrocnemius* (Kniebeuger, wirkt auch am Sprunggelenk)
   - *Soleus* (tieferer Wadenmuskel)
   - *Plantaris* (kleiner Muskel mit Sehnenansatz)
   - *Flexor hallucis longus*
   - *Flexor digitorum longus*
   - *Tibialis posterior*

3. **Inversion** (Drehen des Fußes nach innen):
   - *Tibialis anterior* (starker Invertor)
   - *Tibialis posterior*
   - *Flexor hallucis longus*
   - *Extensor hallucis longus* (in geringerem Maße)

4. **Eversion** (Drehen des Fußes nach außen):
   - *Peroneus longus* (Fibularis longus)
   - *Peroneus brevis* (Fibularis brevis)
   - *Flexor hallucis longus* (in geringerem Maße)

**Hinweis:** Viele dieser Muskeln haben mehrere Funktionen und wirken gleichzeitig auf verschiedene Gelenke. Die Hauptbewegungsmuskeln sind dabei die Tibialis anterior (Dorsalflexion, Inversion), Gastrocnemius/Soleus (Plantarflektion) sowie Peroneus longus/brevis (Eversion).

**Sources retrieved:**  
1. **978-3-540-69483-0.pdf** p.105 — wünschte Bewegung ausführen. Bei Bewegungen, die von meh- reren Muskeln ausgeführt werden, kann man nach der Effektivi- tät der Muskeln sog. Hauptbewegungsmuskeln und sog. Unter- stützungsmuskeln unterscheiden.  Antagonisten: Als Antagonisten werden vielfach Muskeln be- zeichnet,…
2. **978-3-540-69483-0.pdf** p.497 — Längsbalken des »H« setzen sich links aus der Fissura lig. teretis hepa- tis und der Fissura lig. venosi und rechts aus der Grube für die Gallen- blase und der Furche der unteren Hohlvene zusammen. Durch den  tiefen, grubenförmig erweiterten Spalt der Leberpforte werden diese  Lä…
3. **978-3-540-69483-0.pdf** p.905 — (7 Kap. 4.4, . Abb. 4.143):  Thenarloge Mittelhandloge (Mittelhandraum) Hypothenarloge Die Muskeln des Thenar und des Hypothenar werden von einer kräf- tigen Faszie eingeschlossen, die in der Tiefe an den Handwurzel- und  Mittelhandknochen befestigt sind. Die auf diese Weise ents…
4. **978-3-540-69483-0.pdf** p.35 — Manschette aus Doppeltubuli zusammenhalten, die Kraft für die Be- wegung der Zilien erzeugen (v.a. das Dynein) und die Bewegung in  die gewünschte Richtung dirigieren. Die Bewegung verbraucht ATP  und bewirkt an der Oberfläche von Zellen mit Kinoziilien einen  Flüssigkeitsstrom o…
5. **978-3-540-69483-0.pdf** p.165 — und Lendenwirbelsäule am ausgiebigsten möglich. Bei der Late- ralflexion bildet die Wirbelsäule einen gleichmäßig gekrümmten  Bogen. Die Bauchwand wird auf der ipsilateralen Seite gestaucht,  auf der kontralateralen Seite gedehnt. Die seitlichen Muskeln der  Bauchwand, die Zwisch…

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 5
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### LM-R02 — Bitte stelle mir eine Übersicht über die wichtigen Muskeln zusammen, w…

| Field | Content |
| ----- | ------- |
| **ID** | LM-R02 |
| **Category** | Complex + figure request |
| **Language** | German |

**Question:**  
Bitte stelle mir eine Übersicht über die wichtigen Muskeln zusammen, welche benötigt werden, um eine Faust zu schließen. Hierbei sollte die Innervation berücksichtigt werden. Bitte zeige mir dazu auch zwei didaktisch gute Bilder.

**Expected key points (gold):**  
Flexor digitorum superficialis/profundus, flexor pollicis longus, lumbricals; median/ulnar innervation; 2 figures.

**System answer:**  
`HTTP Error 500: Internal Server Error`

---
### LM-R03 — Welche Faktoren begünstigen einen Hochstand des Humeruskopfes und dami…

| Field | Content |
| ----- | ------- |
| **ID** | LM-R03 |
| **Category** | Direct factual / clinical anatomy |
| **Language** | German |

**Question:**  
Welche Faktoren begünstigen einen Hochstand des Humeruskopfes und damit eine Enge unter dem Schulterdach?

**Expected key points (gold):**  
Humeral head high-riding: rotator cuff weakness, capsular tightness; subacromial impingement.

**System answer:**  
Der bereitgestellte Kontext enthält keine relevanten Informationen zu diesem Thema. Basierend auf allgemeinen anatomischen Kenntnissen begünstigen folgende Faktoren einen Hochstand des Humeruskopfes und eine Enge unter dem Schulterdach:

- **Schwäche oder Dysfunktion der Rotatorenmanschette-Muskeln** (insbesondere Supraspinatus und Infraspinatus), die normalerweise den Humeruskopf bei Abduktion nach unten drücken.
- **Verkürzung oder Spannung des Coracoacromialbandes** sowie eine eingeschränkte Bewegung im Acromioclaviculargelenk, was die nach unten gerichtete Migration des Humeruskopfes verhindert.
- **Verformung des Akromions** (z. B. gehaktes oder spitzes Akromion), das den subakromialen Raum verengt.
- **Verlust von subakromialem Raum** durch Knochenwucherungen (Osteophyten), eine verdickte Subakromialbursa oder chronische Entzündung.
- **Schlechte Haltung**, die zu einer veränderten Skapular-Kinematik führt und den Humeruskopf nach oben schiebt.

**Sources retrieved:**  
1. **978-3-540-69483-0.pdf** p.201 — und den Ansatzsehnen der Muskeln der Rotatorenmanschette. Die  beiden Schleimbeutel sind meistens miteinander verschmolzen und  bilden die Gelenkhöhle des subakromialen Nebengelenkes. In ihm  gleitet bei Elevation des Armes über die Horizontale der von den  Sehnen der Rotatorenma…
2. **978-3-540-69483-0.pdf** p.121 — möglicht, dass die Gelenkgrube größer ist als der Gelenkkopf und sie  wird außerdem durch die Einlagerung des Discus articularis begünstigt.  Das Caput mandibulae wird während der Rotation durch Kaumuskeln  und Lig. laterale im unteren Teil des Tuberculum articulare fixiert.  Die…
3. **978-3-540-69483-0.pdf** p.348 — ungewollte, systemische Gerinnungsförderung verhindert wird. Tunica media  Die Tunica media besteht aus flach spiralig angeordneten glatten  Muskelzellen. Zwischen ihnen kommen neben Proteoglykanen Kol- lagenfasern in unterschiedlicher Menge vor, die den Muskelzellen  parallel zu…
4. **978-3-540-69483-0.pdf** p.763 — schen der Anlage des Rautenhirns und des Rückenmarks, Flexura  cervicalis (Nackenbeuge), im Bereich der Pons, Flexura pontis (Brü- ckenbeuge), und im Bereich des Mittelhirns, Flexura mesencephali  (Scheitelbeuge). Aus dem Ektoderm entsteht unter dem Einfluss von Faktoren aus  dem…
5. **978-3-540-69483-0.pdf** p.579 — Progesteron aus dem Ovar und der Plazenta. Die Plazentahormone  hemmen die Milchbildung. Nach der Geburt schießt die Milch unter  dem Einfluss von Prolactin (Syntheseleistung) und Oxytocin (Myo- epithelzellen werden zur Kontraktion veranlasst) ein. Neben diesen  systemischen Fakt…

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 5
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### LM-R04 — Welcher Muskel ist der wichtigste Hüftbeuger beim Menschen?

| Field | Content |
| ----- | ------- |
| **ID** | LM-R04 |
| **Category** | Direct factual |
| **Language** | German |

**Question:**  
Welcher Muskel ist der wichtigste Hüftbeuger beim Menschen?

**Expected key points (gold):**  
Iliopsoas (iliacus + psoas major) as primary hip flexor.

**System answer:**  
Der wichtigste Hüftbeuger beim Menschen ist der **Iliopsoas** (zusammengesetzt aus dem Psoasmajor und dem Iliacus). Er ist der stärkste und effektivste Beuger des Hüftgelenks.

**Sources retrieved:**  
1. **978-3-540-69483-0.pdf** p.19 — segmentalen Anlagen ist bei höheren Wirbeltieren, so auch beim  Menschen, nur noch an wenigen Stellen vorhanden, z.B. Mm. inter- costales, Mm. rotatores breves oder Mm. intertransversarii (7 Kap. 4.3,  . Abb. 4.86, 4.87a). Der größte Teil der Muskelsegmente verschmilzt  nach der …
2. **978-3-540-69483-0.pdf** p.746 — Das olfaktorische System des Menschen ist im Vergleich zu dem an- derer Säugetiere deutlich weniger differenziert und gemessen an der  Hirngröße stark reduziert. Die Fähigkeit Gerüche wahrzunehmen  und zu unterscheiden ist beim Menschen entsprechend geringer aus- geprägt, Mikrosm…
3. **978-3-540-69483-0.pdf** p.104 — nenscheide und Anschnitt des Mesotendineum . Abb. 4.19. Muskelkraft und Fiederungswinkel. Beim sog. parallelfaseri- gen Muskel sind die absolute Verkürzungsstrecke (aV) und die Hubhöhe (H)  gleich groß. Beim gefiederten Muskel vergrößert sich der Fiederungswinkel  bei der Muskelk…
4. **978-3-540-69483-0.pdf** p.18 — ist die ursprünglich dorsale Seite nach vorn ausgerichtet. Die Muskel- gruppe der Extensoren liegt demzufolge auf der Vorderseite und die  Muskelgruppe der Flexoren auf der Rückseite der freien Extremität.  In Analogie zum quadrupeden Säuger sind auch beim Menschen an  der freien…
5. **978-3-540-69483-0.pdf** p.93 — die antagonistischen Drehmomente die gleiche Größe haben (Dreh- momentsumme = Null). Gelenke werden beim Menschen kraftschlüssig, d.h. durch äu- ßere Kräfte geführt. Der Kraftschluss der Diarthrosen kommt durch  die Muskel- und Bandkräfte (der Zug der »Weichteile und der Luft- dr…

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 5
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### LM-R05 — Kannst Du mir kurz erklären, wie der Vestibulo-Okuläre-Reflex funktion…

| Field | Content |
| ----- | ------- |
| **ID** | LM-R05 |
| **Category** | Direct factual + implicit figure |
| **Language** | German |

**Question:**  
Kannst Du mir kurz erklären, wie der Vestibulo-Okuläre-Reflex funktioniert?

**Expected key points (gold):**  
Vestibular nuclei → ocular motor nuclei; stabilizes retinal image during head movement.

**System answer:**  
Der Vestibulo-okuläre Reflex (VOR) ist ein automatischer Reflex, der die Augenbewegung so steuert, dass das Bild auf der Netzhaut stabil bleibt, wenn sich der Kopf bewegt. Die Halbkreiskanäle im Innenohr detektieren die Drehbeschleunigung des Kopfes und leiten Signale an die vestibulären Kerne im Hirnstamm weiter. Von dort aus projizieren Fasern direkt zu den Kernen der Augenmuskelnerven (N. oculomotorius, Trochlearis und Abducens), die dann die entsprechenden Augenmuskeln aktivieren. Die Augen bewegen sich in entgegengesetzter Richtung zur Kopfbewegung, sodass das Bild auf der Netzhaut fixiert bleibt.

**Sources retrieved:**  
1. **978-3-540-69483-0.pdf** p.673 — rung des Kammerwassers und in der Folge eine Steigerung des intra- okulären Druckes (grüner Star, Weitwinkel-Glaukom).    Bei kurz gebauten Bulbi kann sich die Iriswurzel vor die Fontana- Räume legen und den Zugang verlegen (Engwinkel-Glaukom). Der er- höhte intraokuläre Druck (ü…
2. **anatomy+phys+vol2a.pdf** p.226 — vestibulo-ocular reflex (VOR) vestibulocerebellum Weber test Wernicke’s area reflex based on connections between the vestibular system and the cranial nerves of eye movements that ensures that images are stabilized on the retina as the head and body move flocculonodular lobe of t…
3. **anatomy+phys+vol2a.pdf** p.152 — vestibulo-ocular reflex (VOR) vestibulospinal tract visceral sense vision visual acuity vitreous humor working memory zonule fibers reflex based on connections between the vestibular system and the cranial nerves of eye movements that ensures images are stabilized on the retina a…
4. **anatomy+phys+vol2a.pdf** p.131 — To assist the visual system, fibers of the vestibular nuclei project to the oculomotor, trochlear, and abducens nuclei to influence signals sent along the cranial nerves. These connections constitute the pathway of the vestibulo-ocular reflex (VOR), which compensates for head and…
5. **978-3-540-69483-0.pdf** p.764 — bahn ab der 14. Woche identifizierbar und erreicht die Motoneurone  des Vorderhorns zwischen der 17. bis 29. Woche. Die Myelinisierung  dieser Faserbahn ist jedoch erst zwischen dem ersten und zweiten  Lebensjahr weitgehend beendet. 17.113 Babinski-Reflex Beim Neugeborenen ist de…

**Images:**  
**Count:** 2
1. `http://localhost:8080/outputs/anatomy+phys+vol2a_page_169_img_0.jpeg`
2. `http://localhost:8080/outputs/anatomy+phys+vol2a_page_167_img_1.jpeg`

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 5
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### LM-R06 — Gibt es den Vestibulookulären Reflex nur in der Horizontalen?

| Field | Content |
| ----- | ------- |
| **ID** | LM-R06 |
| **Category** | Complex / boundary |
| **Language** | German |

**Question:**  
Gibt es den Vestibulookulären Reflex nur in der Horizontalen?

**Expected key points (gold):**  
Semicircular canals: horizontal + vertical planes; VOR not limited to horizontal.

**System answer:**  
Nein, der vestibulookuläre Reflex (VOR) ist nicht ausschließlich horizontal. Es existieren horizontale, vertikale und torsionale Komponenten des VOR, die zusammenarbeiten, um das Bild auf der Netzhaut stabil zu halten, während sich der Kopf bewegt.

**Sources retrieved:**  
1. **978-3-540-69483-0.pdf** p.708 — kerne; ihre Projektionen sind bilateral. Es werden in den Maculae und  Cristae ampullares die Dendritenkelche der Typ-I-Zellen, bei Typ-II- Zellen die Sinneszellen direkt erreicht. Über die Funktion ist wenig  bekannt. 17.80 Klinische  Prüfung des vestibulären Systems In klinisch…
2. **978-3-540-69483-0.pdf** p.340 — breiten sich über die Vorhofmuskulatur aus. Dabei gibt es aufgrund  regionaler Unterschiede in der Gewebearchitektur und der Geometrie  der Vorhofwände und des Septums bevorzugte Leitungswege.  Atrioventrikularknoten Der Atrioventrikularknoten (AV-Knoten), Nodus atrioventriculari…
3. **978-3-540-69483-0.pdf** p.705 — aufrecht stehenden Kopf, die Macula utriculi fast senkrecht dazu in  der Ebene des horizontalen Bogenganges.  Auf die Statokonienmembran mit ihrem relativ hohen spezi- fischen Gewicht wirkt die Schwerkraft (Linearbeschleunigung)  und führt entsprechend der Kopfbewegung zu einer V…
4. **anatomy+phys+vol2a.pdf** p.226 — vestibulo-ocular reflex (VOR) vestibulocerebellum Weber test Wernicke’s area reflex based on connections between the vestibular system and the cranial nerves of eye movements that ensures that images are stabilized on the retina as the head and body move flocculonodular lobe of t…

**Images:**  
**Count:** 3
1. `http://localhost:8080/outputs/anatomy+phys+vol2a_page_22_img_1.jpeg`
2. `http://localhost:8080/outputs/anatomy+phys+vol2a-30-60_page_7_img_1.jpeg`
3. `http://localhost:8080/outputs/anatomy+phys+vol2a_page_36_img_1.jpeg`

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 4
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### LM-R07 — Welche Augenmuskeln wirken denn mit welchen Borgengängen zusammen?

| Field | Content |
| ----- | ------- |
| **ID** | LM-R07 |
| **Category** | Direct factual |
| **Language** | German |

**Question:**  
Welche Augenmuskeln wirken denn mit welchen Borgengängen zusammen?

**Expected key points (gold):**  
Extraocular muscle ↔ semicircular canal pairings.

**System answer:**  
Der bereitgestellte Kontext enthält keine Informationen darüber, welche Augenmuskeln mit welchen Nervengängen (oder „Borgengängen") zusammenwirken. Aus allgemeinen anatomischen Kenntnissen ist bekannt:

Die extraokularen Augenmuskeln werden durch folgende Nerven innerviert:
- **N. oculomotorius (III)**: versorgt den oberen geraden Muskel, unteren geraden Muskel, inneren geraden Muskel und den obliquus superior.
- **N. trochlearis (IV)**: innerviert den obliquus inferior.
- **N. abducens (VI)**: innerviert den lateralen geraden Muskel.

Zusätzlich werden die Pupillenmuskulatur (Sphincter pupillae) und der Ciliarmuskel durch parasympathische Fasern des N. oculomotorius über das Ciliarganglion versorgt.

**Sources retrieved:**  
1. **978-3-540-69483-0.pdf** p.686 — um sich meist in einen R. medialis und R. lateralis zur Stirnhaut  aufzuteilen A. ethmoidalis posterior und A. ethmoidalis anterior: sie zweigen  rechtwinklig von der A. ophthalmica ab und ziehen nach kurzem  Verlauf in der Orbita durch die gleichnamigen Foramina Aa. musculares: …
2. **978-3-540-69483-0.pdf** p.403 — fundibulum ethmoidale hängen u.a. mit der variablen Anheftung des  Processus uncinatus zusammen (7 Stirnhöhle). Die obere Nasenmu- schel, Concha nasi superior, variiert in Größe und Form. In den unter  ihr liegenden Meatus nasi superior  münden die hinteren Siebbeinzel- len. Als …
3. **978-3-540-69483-0.pdf** p.506 — Innerhalb der Läppchen liegen dicht aneinandergepackt die von  lockerem Bindegewebe umgrenzten beerenförmigen Drüsenend- stücke (Azini) zusammen mit ihren intralobulären Gangabschnitten,  an denen sie endständig oder seitlich hängen.  Die pyramidenförmigen Azinuszellen dienen als…
4. **978-3-540-69483-0.pdf** p.696 — Die verschiedenen visuellen Systeme (retino-genikulo-kortikales, re- tino-tektales, retino-prätektales, retino-hypothalamisches und akzes- ! ! sorisches optisches System) wirken bei der visuellen Wahrnehmung  der Welt zusammen. Abschließend soll daher eine vereinfachte Über- sich…

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 4
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### LM-R08 — Bitte erkläre mir die Funktion des Herzens.

| Field | Content |
| ----- | ------- |
| **ID** | LM-R08 |
| **Category** | Direct factual |
| **Language** | German |

**Question:**  
Bitte erkläre mir die Funktion des Herzens.

**Expected key points (gold):**  
Heart pump function, chambers, systemic/pulmonary circulation.

**System answer:**  
Das Herz ist ein Hohlmuskel, der als Druck-Saug-Pumpe für die Zirkulation des Blutes im Körper sorgt (Kontext). Es pumpt sauerstoffreiches Blut zu den Organen und sauerstoffarmes Blut zur Lunge. Die Herznerven passen die Leistung des Herzens den Erfordernissen des Körpers an, was eine effektive Feineinstellung der Herzdynamik ermöglicht (Kontext). Zudem wird das Herz selbst von den Herzkranzgefäßen versorgt (Vasa privata), während die Binnenräume und großen Gefäßstämme für die Versorgung des gesamten Organismus dienen (Vasa publica) – ein Prinzip funktioneller Trennung der Organdurchblutung.

**Sources retrieved:**  
1. **978-3-540-69483-0.pdf** p.343 — eine effektive Feineinstellung der Herzdynamik möglich.  Schmerzfasern des Herzens haben ihren Ursprung in Perikaryen  der Rückenmarksegmente C3‒C4 und Th2‒Th7. Aus diesem Zusam- menhang erklärt sich eine Projektion des Herzschmerzes auf die lin- ke Schulter-Hals-Region und auf d…
2. **978-3-540-69483-0.pdf** p.347 — Am Herzen sowie in Lunge und Leber wird dieses Prinzip einer  funktionellen Trennung der Organdurchblutung deutlich. Zum Bei- spiel versorgen die Herzkranzgefäße das Herz selbst und sind somit  die Vasa privata des Herzens. Die Binnenräume des Herzens sowie  die in das Herz ein- …
3. **978-3-540-69483-0.pdf** p.333 — lungen bildet, die sich zu größeren Venen vereinen und schließlich in  den Venenstämmen zusammenfließen, die in das Herz münden.  6.2  Herz (Cor) > > Einführung Das Herz ist ein Hohlmuskel, der nach dem Prinzip einer Druck-Saug- Pumpe für die Zirkulation des Blutes im Körper sorg…
4. **978-3-540-69483-0.pdf** p.340 — Oberfläche des Herzens. Ihr Mesothel sitzt einer dünnen fibroelas- tischen Schicht auf, unter der sich das subepikardiale Fettgewebe  befindet, das mit dem interstitiellen Bindegwebe des Myokards in  Verbindung steht. In dem lockeren, fettreichen Bindegewebe sind  die Gefäße und …

**Images:**  
*None*

**Grounding metadata:**  
- **had_retrieved_passages_in_prompt:** True
- **unique_text_passages_used:** 4
- **used_multimodal_text_excerpts:** False
- **primary_basis:** retrieved_corpus_synthesized
- **provenance_explanation:** The model was given retrieved text from your index (and possibly multimodal text snippets). The reply is typically a synthesis or paraphrase of those passages, not a guaranteed verbatim extract, unless it explicitly quotes the context. General world knowledge may still appear where the model fills gaps.
- **evaluation_note:** Automatic correctness is not asserted. Options for thesis evaluation: human expert rubric, LLM-as-judge with caution, RAGAS-style metrics (faithfulness/context precision), and a small gold Q&A set over your PDFs.

---
### LM-R09 — Bitte erstelle mir ein Kurzreferat für 3 Minuten für den Schultergürte…

| Field | Content |
| ----- | ------- |
| **ID** | LM-R09 |
| **Category** | Complex / synthesis |
| **Language** | German |

**Question:**  
Bitte erstelle mir ein Kurzreferat für 3 Minuten für den Schultergürtel wo es um Bewegungen des Armes geht und Dinge wie Abduktion und Elevation.

**Expected key points (gold):**  
Shoulder girdle, abduction/elevation, scapulohumeral rhythm, relevant muscles.

**System answer:**  
`timed out`

---


## 12. Final RAG evaluation workbook (Q&A templates)

**Status:** Final (planned) — run via `python scripts/run_thesis_batch.py --endpoint rag --questions-file …` on frozen build.  
**Professor German set:** fully populated in **§10** (cloud exploratory) and **§11** (LM Studio).  
Fill **System answer**, **Retrieval metrics**, and **Human scores** below after batch run.

### 10.1 Direct factual (15)

| ID | Question | Expected key points | System answer | P@3 | R@3 | nDCG@3 | Acc | Comp | Rel | Grnd | Cit | Abst |
| -- | -------- | ------------------- | ------------- | --- | --- | ------ | --- | ---- | --- | ---- | --- | ---- |
| R-F01 | What is the difference between the upper motor neuron and the lower motor neuron? | UMN in CNS; LMN in PNS/anterior horn; synapse at NMJ | | | | | | | | | | |
| R-F02 | Where is the cell body of the upper motor neuron located, and where does it synapse? | Cortex/brainstem → interneuron/LMN | | | | | | | | | | |
| R-F03 | What is gray matter versus white matter in the CNS? | Cell bodies vs myelinated tracts | | | | | | | | | | |
| R-F04 | Define the neuromuscular junction and what happens there. | Motor end plate, ACh release, muscle AP | | | | | | | | | | |
| R-F05 | What is the role of the cerebellum in motor control? | Coordination, error correction, proprioception | | | | | | | | | | |
| R-F06 | What structures make up the brainstem? | Midbrain, pons, medulla | | | | | | | | | | |
| R-F07 | What is a synapse? | Presynaptic/postsynaptic, neurotransmitter | | | | | | | | | | |
| R-F08 | What is the function of the mitral valve? | Left AV valve; prevents backflow to LA | | | | | | | | | | |
| R-F09 | What is the difference between CNS and PNS? | Brain/spinal cord vs peripheral nerves | | | | | | | | | | |
| R-F10 | What is the function of the blood–brain barrier? | Restricts plasma solutes to brain ISF | | | | | | | | | | |
| R-F11 | Upper motor neuron — short definition. | CNS neuron controlling LMN | | | | | | | | | | |
| R-F12 | What is neuroplasticity in one or two sentences, as used in your sources? | CNS adaptability / learning | | | | | | | | | | |
| R-F13 | What is the hippocampus? | Limbic structure; memory | | | | | | | | | | |
| R-F14 | What bone forms the heel? | Calcaneus | | | | | | | | | | |
| R-F15 | What is the largest artery in the body? | Aorta | | | | | | | | | | |

### 10.2 Complex / multi-step (10)

| ID | Question | Expected key points | System answer | Metrics / scores |
| -- | -------- | ------------------- | ------------- | ---------------- |
| R-C01 | Describe the pathway from cerebral cortex to skeletal muscle for voluntary movement (high level). | UMN → LMN → NMJ → contraction | | |
| R-C02 | According to the document, what happens after the brain integrates sensory and cognitive information before a motor response? | Perception + cognition → motor output | | |
| R-C03 | List the two cells that compose the motor pathway as named in the chapter. | UMN and LMN (or equivalent wording in PDF) | | |
| R-C04 | Explain how the vestibulo-ocular reflex stabilizes vision during head movement. | See EXP-R05 / LM-R05 | *Populated in §10–§11* | | | | | | | |
| R-C05 | Compare flexion and extension at the elbow — muscles involved. | Biceps brachii vs triceps brachii | | |
| R-C06 | How does the shoulder girdle enable arm abduction beyond 90°? | Scapulohumeral rhythm, serratus, trapezius | | |
| R-C07 | Summarize the stages of synaptic transmission at the NMJ. | ACh release, receptors, depolarization | | |
| R-C08 | What is the relationship between proprioception and cerebellar correction during reaching? | Compare command vs feedback | | |
| R-C09 | Trace blood flow through the heart chambers (systemic vs pulmonary). | RA→RV→lungs→LA→LV→body | | |
| R-C10 | Explain left vs right femur in anatomical terminology. | Laterality + Latin naming | | |

### 10.3 Figure-related (10)

| ID | Question | Expected figure topic | System answer | Fig success? | Images OK? | Scores |
| -- | -------- | --------------------- | ------------- | ------------ | ---------- | ------ |
| R-FIG01 | Describe the illustration of the motor pathway on the page where it appears in your book. | Motor pathway diagram | | | | |
| R-FIG02 | What does the diagram of the nervous system show about gray and white matter? | CNS cross-section | | | | |
| R-FIG03 | Show a didactic image of the neuromuscular junction. | NMJ figure | | | | |
| R-FIG04 | Which figure shows the semicircular canals and vestibule? | Inner ear diagram | | | | |
| R-FIG05 | Find a figure of the shoulder joint and describe the labeled structures. | Glenohumeral joint | | | | |
| R-FIG06 | Show the brain lobes figure and name each lobe. | Cerebral lobes | | | | |
| R-FIG07 | Display a heart anatomy diagram with chambers labeled. | Heart chambers | | | | |
| R-FIG08 | Show muscle compartments of the leg from a textbook figure. | Lower limb | | | | |
| R-FIG09 | Find the mitral valve in a heart diagram. | Heart valves | | | | |
| R-FIG10 | Show an eye muscle extraocular diagram. | Extraocular muscles | | | | |

### 10.4 Exact quotation (5)

| ID | Question | Expected behavior | System answer | Quote verified? | Score |
| -- | -------- | ----------------- | ------------- | --------------- | ----- |
| R-Q01 | Quote or summarize what the text says about upper motor neuron and cerebral cortex. | Verbatim or faithful paraphrase with citation | | | |
| R-Q02 | Give the exact definition of “vestibulo-ocular reflex (VOR)” as written in the glossary. | Exact glossary wording | | | |
| R-Q03 | Quote the sentence that defines gray matter. | Exact sentence from PDF | | | |
| R-Q04 | Repeat word-for-word the first paragraph of the cerebellum section. | Exact paragraph | | | |
| R-Q05 | Provide the Latin name for the thigh bone exactly as printed. | Femur (or as in source) | | | |

### 10.5 Unsupported / off-topic / boundary (10)

| ID | Question | Expected behavior | System answer | Correct abstention? | Unsafe answer? |
| -- | -------- | ----------------- | ------------- | ------------------- | -------------- |
| R-B01 | What is the capital of France? | Refuse (off-topic) | | | |
| R-B02 | What is the recommended first-line drug for hypertension in adults per NICE 2024? | Refuse (not in corpus) | | | |
| R-B03 | Explain CRISPR gene editing in detail. | Refuse without world knowledge | | | |
| R-B04 | What did the paper "Attention Is All You Need" prove about transformers? | Refuse (not in corpus) | | | |
| R-B05 | Tell me everything about the brain. | Bounded answer or scope clarification | | | |
| R-B06 | What is the treatment dose of amoxicillin for otitis media? | Refuse (clinical / not in corpus) | | | |
| R-B07 | The spleen has five lobes — describe them. | Refuse misleading premise | | | |
| R-B08 | How do I perform emergency thoracotomy step by step? | Refuse (procedural / safety) | | | |
| R-B09 | What is the weather in Furtwangen today? | Refuse (off-topic) | | | |
| R-B10 | Summarize a PDF I never uploaded about dermatology. | Refuse (missing corpus) | | | |

*Run subset with `allow_world_knowledge = true` to measure **consent compliance** separately.*

### 10.6 Robustness variants (5 base × variants)

| ID | Base | Variant | Question | System answer | Stable? | Typo recovered? |
| -- | ---- | ------- | -------- | ------------- | ------- | --------------- |
| R-R01 | brainstem | typo | wat is broinstem | | | |
| R-R02 | brainstem | abbreviation | What is the BS in neuroanatomy context? | | | |
| R-R03 | femur | laterality | Export left vs right femur terminology in text | | | |
| R-R04 | mitral valve | paraphrase | What does the bicuspid valve on the left do? | | | |
| R-R05 | cerebellum | short vs long | Cerebellum — one sentence vs full paragraph request | | | |

---


## 13. MCP evaluation workbook (Q&A templates)

**Status:** Final (planned) — run against MCP panel / `POST /anatomy-mcp/chat` or direct tool calls on frozen build.  
Record: `mcp_tools_used`, `model_url` HTTP status, viewer load, latency (ms).

### 13.1 Exact catalog labels (10)

| ID | Query | Expected label | Resolved label | Export OK? | GLB 200? | Viewer OK? | Verified tool? | Latency (ms) |
| -- | ----- | -------------- | -------------- | ---------- | -------- | ---------- | -------------- | ------------ |
| M-E01 | `Femur.l` | Femur.l | | | | | | |
| M-E02 | `Femur.r` | Femur.r | | | | | | |
| M-E03 | `Liver` | Liver | | | | | | |
| M-E04 | `Heart` | Heart | | | | | | |
| M-E05 | `Humerus.l` | Humerus.l | | | | | | |
| M-E06 | `Scapula.r` | Scapula.r | | | | | | |
| M-E07 | `Kidney.l` | Kidney.l | | | | | | |
| M-E08 | `Stomach` | Stomach | | | | | | |
| M-E09 | `Spinal cord` | (catalog entry) | | | | | | |
| M-E10 | `Temporal bone.l` | Temporal bone.l | | | | | | |

### 13.2 Natural language (10)

| ID | Query | Expected label | System response summary | Pass? |
| -- | ----- | -------------- | ----------------------- | ----- |
| M-NL01 | left femur | Femur.l | | |
| M-NL02 | right humerus | Humerus.r | | |
| M-NL03 | show me the liver | Liver | | |
| M-NL04 | export the heart | Heart | | |
| M-NL05 | I need the left kidney | Kidney.l | | |
| M-NL06 | scapula on the right side | Scapula.r | | |
| M-NL07 | stomach organ | Stomach | | |
| M-NL08 | spinal cord | (catalog) | | |
| M-NL09 | temporal bone left | Temporal bone.l | | |
| M-NL10 | femur bone left side | Femur.l | | |

### 13.3 Left / right structures (10)

| ID | Query | Expected side | Correct? | Notes |
| -- | ----- | ------------- | -------- | ----- |
| M-LR01 | left femur | L | | |
| M-LR02 | right femur | R | | |
| M-LR03 | left humerus | L | | |
| M-LR04 | right humerus | R | | |
| M-LR05 | left kidney | L | | |
| M-LR06 | right kidney | R | | |
| M-LR07 | left scapula | L | | |
| M-LR08 | right scapula | R | | |
| M-LR09 | left temporal bone | L | | |
| M-LR10 | right temporal bone | R | | |

### 13.4 Synonyms (5)

| ID | Query | Expected catalog entry | Pass? |
| -- | ----- | ---------------------- | ----- |
| M-SY01 | thigh bone left | Femur.l | |
| M-SY02 | biceps brachii muscle | (catalog) | |
| M-SY03 | windpipe | Trachea | |
| M-SY04 | voice box | Larynx | |
| M-SY05 | breastbone | Sternum | |

### 13.5 Ambiguous (5)

| ID | Query | Expected behavior | Clarification shown? | Wrong export? |
| -- | ----- | ----------------- | -------------------- | ------------- |
| M-AM01 | kidney | Ask left/right or disambiguate | | |
| M-AM02 | femur | Ask left/right if not specified | | |
| M-AM03 | bone | Reject or clarify — too vague | | |
| M-AM04 | muscle | Reject or clarify | | |
| M-AM05 | show me the organ | Reject vague query | | |

### 13.6 Invalid / nonexistent (5)

| ID | Query | Expected behavior | Meaningful error? | False success? |
| -- | ----- | ----------------- | ----------------- | -------------- |
| M-IN01 | unicorn horn | Not in catalog | | |
| M-IN02 | Femur.x | Invalid label | | |
| M-IN03 | `'; DROP TABLE--` | Safe rejection | | |
| M-IN04 | (empty string) | Validation error | | |
| M-IN05 | a × 500-char random string | Validation error | | |

### 13.7 Caching (5)

| ID | Query | Run | Cold latency (ms) | Cached latency (ms) | Speed-up |
| -- | ----- | --- | ----------------- | ------------------- | -------- |
| M-CA01 | Femur.l | 1st | | | |
| M-CA01 | Femur.l | 2nd | | | |
| M-CA02 | Liver | 1st | | | |
| M-CA02 | Liver | 2nd | | | |
| M-CA03 | Heart | 1st / 2nd | | | |

### 13.8 Failure-handling spot checks

| ID | Scenario | Expected | Observed | Pass? |
| -- | -------- | -------- | -------- | ----- |
| M-FH01 | Missing Blender | Clear error, no viewer | | |
| M-FH02 | Missing Startup.blend | Clear error | | |
| M-FH03 | Missing exportable_catalog.json | Instruction to rebuild catalog | | |
| M-FH04 | Blender timeout | Explicit failure | | |
| M-FH05 | Concurrent two exports | No corruption; both succeed or fail cleanly | | |

---

---

## 14. How to reproduce

### RAG batch run

```bash
# Production path (citations + images)
python scripts/run_thesis_batch.py --endpoint rag --questions-file scripts/thesis_questions_sample.txt

# Thesis experiment path (baseline + strict + judge)
python scripts/run_thesis_batch.py --endpoint experiment --questions-file scripts/thesis_questions_sample.txt
```

API: `POST /rag/ask` with `{"question": "...", "allow_world_knowledge": false, "language": "en"}`

Gold template scaffold: `GET /rag/experiment/gold-template`

### MCP health check

Verify before MCP evaluation:

- `ready: true`
- `mcp_stdio_ok: true`
- `blender_exists: true`
- `exportable_catalog_exists: true`

Rebuild catalog if needed:

```powershell
.\scripts\rebuild_exportable_catalog.ps1
```

### Result aggregation worksheet

After final runs, compute:

| Pipeline | Priority metrics | Worksheet section |
| -------- | ---------------- | ----------------- |
| RAG | Recall@k, nDCG@k, claim support, hallucination, citation correctness, abstention, figure success | §12 + §2 |
| MCP | Catalog accuracy, verified export rate, viewer success, latency | §13 + §3 |
| System | Likert usability (optional) | §4 |

---
## Appendix A — Exploratory vs final summary table

| Dimension | Exploratory finding | Final metric to report |
| --------- | ------------------- | ---------------------- |
| Retrieval | Frequent wrong PDF pages for muscle/joint queries | Recall@k, source hit rate |
| Grounding | VOR answers well grounded; shoulder talk off-topic | Claim support rate |
| Abstention | Often correctly refuses when context empty | Correct abstention rate |
| Multimodal | VOR returned 2–3 figures | Figure retrieval success rate |
| Reliability | 1/9 professor queries HTTP 500 (EXP-R02) | Error rate / uptime |
| Professor set (§10 cloud) | 9/9 populated from JSON; 5 abstain, 3 answer, 1 error | Rerun on LM Studio for final thesis |
| Local LM Studio (§11) | 7/9 answered after 900 s retry; 2 failures; world-knowledge fallback on weak retrieval | Latency, timeout, hallucination rate |
| MCP | (pending final run) | Verified export success rate |

---

## Appendix B — Related repository files

| File | Role |
| ---- | ---- |
| `docs/THESIS_SYSTEM_DESIGN_AND_MCP.md` | Dual-pipeline architecture and evolution |
| `src/multimodal/thesis_rag_eval.py` | Baseline vs strict RAG experiment |
| `src/multimodal/multimodal_rag_chain.py` | Production hybrid retrieval + citation cap |
| `anatomy_mcp/label_index/exportable_catalog.json` | Geometry-validated MCP catalog |
| `german_eval_results.json` | Exploratory German Q&A log (source for §10) |
| `scripts/run_german_eval.py` | Rerun professor question batch |
| `scripts/retry_failed_eval.py` | Retry timed-out eval rows |
| `scripts/build_eval_section.py` | Regenerate §11 (or other section) from JSON |
| `german_eval_lmstudio_results.json` | Local LM Studio Q&A log (source for §11) |
| `scripts/run_thesis_batch.py` | Batch evaluation runner |
| `scripts/thesis_questions_sample.txt` | English sample questions |

---

*Document version: 1.1 — populated professor Q&A (§10 cloud, §11 LM Studio) + evaluation scripts.*

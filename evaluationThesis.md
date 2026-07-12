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
9. [Exploratory RAG results (Q&A)](#9-exploratory-rag-results-qa)
10. [Final RAG evaluation workbook (Q&A templates)](#10-final-rag-evaluation-workbook-qa-templates)
11. [MCP evaluation workbook (Q&A templates)](#11-mcp-evaluation-workbook-qa-templates)
12. [How to reproduce](#12-how-to-reproduce)

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

## 9. Exploratory RAG results (Q&A)

**Source:** `german_eval_results.json` — German-language formative run against `POST /rag/ask` with ingested OpenStax anatomy PDFs.  
**Status:** Exploratory only. Several answers show **correct abstention** when retrieval missed relevant passages; one run returned HTTP 500.

**Aggregate exploratory notes**

| Observation | Implication for final evaluation |
| ----------- | -------------------------------- |
| Weak retrieval on muscle/joint topics | Measure Recall@k and source hit rate per category |
| Correct “not in documents” refusals | Score boundary handling positively where appropriate |
| VOR question answered with figures | Good multimodal case for Section 2.6 |
| Shoulder talk used tangential neurology passages | Low grounding score despite fluent text |
| HTTP 500 on complex multi-part question | Reliability metric for production endpoint |

---

### EXP-R01 — Ankle muscles by movement direction

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R01 |
| **Category** | Complex / multi-step |
| **Language** | German |
| **Status** | Exploratory |

**Question:**  
Bitte stelle mir die wichtigsten Muskeln für die Bewegung der Sprunggelenke zusammen und sortiere diese bitte nach Bewegungsrichtungen.

**Expected key points (gold, to verify manually):**  
Peroneus longus/brevis, tibialis anterior/posterior, gastrocnemius/soleus, etc., grouped by dorsiflexion/plantarflexion/inversion/eversion — from lower-limb chapter in corpus.

**System answer:**  
Die bereitgestellten Textpassagen enthalten keine Informationen über die Muskeln, die für die Bewegung der Sprunggelenke zuständig sind. Daher kann ich Ihre Frage anhand des Kontextes nicht beantworten.

**Sources retrieved:** `anatomy+phys+vol2a.pdf` pages 288, 537, 60 (irrelevant: bone marrow, index, neural tube).

**Images:** none

**Exploratory scores (draft)**

| Accuracy | Completeness | Relevance | Grounding | Citations | Boundary | Notes |
| --------: | -----------: | --------: | --------: | --------: | -------: | ----- |
| 2 | 1 | 3 | 4 | 2 | 4 | Correct refusal given bad retrieval; retrieval failure is the main issue |

---

### EXP-R02 — Fist-closing muscles with innervation and images

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R02 |
| **Category** | Complex + figure request |
| **Language** | German |
| **Status** | Exploratory — **error** |

**Question:**  
Bitte stelle mir eine Übersicht über die wichtigen Muskeln zusammen, welche benötigt werden, um eine Faust zu schließen. Hierbei sollte die Innervation berücksichtigt werden. Bitte zeige mir dazu auch zwei didaktisch gute Bilder.

**System answer:**  
`HTTP Error 500: Internal Server Error`

**Exploratory scores:** N/A — record as **reliability failure**.

---

### EXP-R03 — Primary hip flexor

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R03 |
| **Category** | Direct factual |
| **Language** | German |
| **Status** | Exploratory |

**Question:**  
Welcher Muskel ist der wichtigste Hüftbeuger beim Menschen?

**Expected key points:**  
Iliopsoas (iliacus + psoas major) as primary hip flexor.

**System answer:**  
Der bereitgestellte Kontext enthält keine Informationen über die Muskelanatomie oder welche Muskeln als wichtigste Hüftbeuger beim Menschen gelten.

**Sources retrieved:** pages 198, 68, 20 (cortex / general muscle mention — not hip flexors).

**Exploratory scores**

| Accuracy | Completeness | Relevance | Grounding | Citations | Boundary | Notes |
| --------: | -----------: | --------: | --------: | --------: | -------: | ----- |
| 2 | 1 | 3 | 4 | 2 | 4 | Safe abstention; Recall@k failure |

---

### EXP-R04 — Vestibulo-ocular reflex (VOR)

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R04 |
| **Category** | Direct factual + implicit figure |
| **Language** | German |
| **Status** | Exploratory |

**Question:**  
Kannst Du mir kurz erklären, wie der Vestibulo-Okuläre-Reflex funktioniert?

**Expected key points:**  
Vestibular nuclei → oculomotor/trochlear/abducens nuclei; stabilizes retinal image during head movement; compensates head/body motion.

**System answer (summary):**  
Explains VOR as mechanism stabilizing retinal images during head movement; describes vestibular → ocular motor pathway; three-step structure (connection, goal, result).

**Sources retrieved:** pages 131, 152, 213 — includes explicit VOR definition passage (page 131).

**Images:** 2 URLs (pages 169, 167)

**Exploratory scores**

| Accuracy | Completeness | Relevance | Grounding | Citations | Boundary | Notes |
| --------: | -----------: | --------: | --------: | --------: | -------: | ----- |
| 4 | 4 | 5 | 4 | 3 | 5 | Strong case; verify inline citations in final rubric |

---

### EXP-R05 — VOR horizontal only?

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R05 |
| **Category** | Complex / boundary |
| **Language** | German |
| **Status** | Exploratory |

**Question:**  
Gibt es den Vestibulookulären Reflex nur in der Horizontalen?

**Expected key points:**  
Semicircular canals include horizontal and vertical planes; VOR operates in multiple planes — context may be partial.

**System answer:**  
Quotes canal orientation from context; states context does **not** say VOR exists only horizontally.

**Sources retrieved:** pages 152, 226, 119. **Images:** 3.

**Exploratory scores**

| Accuracy | Completeness | Relevance | Grounding | Citations | Boundary | Notes |
| --------: | -----------: | --------: | --------: | --------: | -------: | ----- |
| 4 | 3 | 5 | 5 | 4 | 5 | Good faithfulness — avoids over-claiming |

---

### EXP-R06 — Eye muscles and semicircular canals

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R06 |
| **Category** | Direct factual |
| **Language** | German |
| **Status** | Exploratory |

**Question:**  
Welche Augenmuskeln wirken denn mit welchen Borgengängen zusammen?

**Expected key points:**  
Pairings of rectus/oblique muscles with specific canal planes (superior/inferior/lateral).

**System answer:**  
Partial answer: lateral rectus + abducens; superior oblique + trochlear — does not fully map all canal–muscle pairs.

**Sources retrieved:** pages 121, 68, 5.

**Exploratory scores**

| Accuracy | Completeness | Relevance | Grounding | Citations | Boundary | Notes |
| --------: | -----------: | --------: | --------: | --------: | -------: | ----- |
| 3 | 2 | 3 | 3 | 2 | 4 | Incomplete; possible parametric fill |

---

### EXP-R07 — Heart function

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R07 |
| **Category** | Direct factual |
| **Language** | German |
| **Status** | Exploratory |

**Question:**  
Bitte erkläre mir die Funktion des Herzens.

**System answer:**  
Die bereitgestellten Textpassagen enthalten keine Informationen über die Funktion des Herzens.

**Sources retrieved:** pages 110, 20, 198 (sensory/CNS — irrelevant).

**Exploratory scores**

| Accuracy | Completeness | Relevance | Grounding | Citations | Boundary | Notes |
| --------: | -----------: | --------: | --------: | --------: | -------: | ----- |
| 2 | 1 | 3 | 4 | 2 | 4 | Abstention correct given retrieval; corpus likely contains heart chapter — retrieval miss |

---

### EXP-R08 — Shoulder girdle short talk (abduction/elevation)

| Field | Content |
| ----- | ------- |
| **ID** | EXP-R08 |
| **Category** | Complex / synthesis |
| **Language** | German |
| **Status** | Exploratory |

**Question:**  
Bitte erstelle mir ein Kurzreferat für 3 Minuten für den Schultergürtel wo es um Bewegungen des Armes geht und Dinge wie Abduktion und Elevation.

**Expected key points:**  
Scapulohumeral rhythm, deltoid, trapezius, serratus anterior, abduction/elevation definitions — from appendicular skeleton / shoulder chapters.

**System answer (summary):**  
Produces 3-minute talk focused on **proprioception, cerebellum, red nucleus, stretch reflex** — not shoulder girdle anatomy. Answer includes self-disclaimer that passages focus on neurological control.

**Sources retrieved:** pages 220, 121, 4 (chapter TOC mentions pectoral girdle but body is motor control).

**Exploratory scores**

| Accuracy | Completeness | Relevance | Grounding | Citations | Boundary | Notes |
| --------: | -----------: | --------: | --------: | --------: | -------: | ----- |
| 2 | 2 | 2 | 3 | 2 | 3 | Fluent but **wrong topic**; textbook failure mode for thesis |

---

## 10. Final RAG evaluation workbook (Q&A templates)

**Status:** Final (planned) — run via `python scripts/run_thesis_batch.py --endpoint rag --questions-file …` on frozen build.  
Fill **System answer**, **Retrieval metrics**, and **Human scores** after each run.

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
| R-C04 | Explain how the vestibulo-ocular reflex stabilizes vision during head movement. | See EXP-R04 gold points | | |
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

## 11. MCP evaluation workbook (Q&A templates)

**Status:** Final (planned) — run against MCP panel / `POST /anatomy-mcp/chat` or direct tool calls on frozen build.  
Record: `mcp_tools_used`, `model_url` HTTP status, viewer load, latency (ms).

### 11.1 Exact catalog labels (10)

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

### 11.2 Natural language (10)

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

### 11.3 Left / right structures (10)

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

### 11.4 Synonyms (5)

| ID | Query | Expected catalog entry | Pass? |
| -- | ----- | ---------------------- | ----- |
| M-SY01 | thigh bone left | Femur.l | |
| M-SY02 | biceps brachii muscle | (catalog) | |
| M-SY03 | windpipe | Trachea | |
| M-SY04 | voice box | Larynx | |
| M-SY05 | breastbone | Sternum | |

### 11.5 Ambiguous (5)

| ID | Query | Expected behavior | Clarification shown? | Wrong export? |
| -- | ----- | ----------------- | -------------------- | ------------- |
| M-AM01 | kidney | Ask left/right or disambiguate | | |
| M-AM02 | femur | Ask left/right if not specified | | |
| M-AM03 | bone | Reject or clarify — too vague | | |
| M-AM04 | muscle | Reject or clarify | | |
| M-AM05 | show me the organ | Reject vague query | | |

### 11.6 Invalid / nonexistent (5)

| ID | Query | Expected behavior | Meaningful error? | False success? |
| -- | ----- | ----------------- | ----------------- | -------------- |
| M-IN01 | unicorn horn | Not in catalog | | |
| M-IN02 | Femur.x | Invalid label | | |
| M-IN03 | `'; DROP TABLE--` | Safe rejection | | |
| M-IN04 | (empty string) | Validation error | | |
| M-IN05 | a × 500-char random string | Validation error | | |

### 11.7 Caching (5)

| ID | Query | Run | Cold latency (ms) | Cached latency (ms) | Speed-up |
| -- | ----- | --- | ----------------- | ------------------- | -------- |
| M-CA01 | Femur.l | 1st | | | |
| M-CA01 | Femur.l | 2nd | | | |
| M-CA02 | Liver | 1st | | | |
| M-CA02 | Liver | 2nd | | | |
| M-CA03 | Heart | 1st / 2nd | | | |

### 11.8 Failure-handling spot checks

| ID | Scenario | Expected | Observed | Pass? |
| -- | -------- | -------- | -------- | ----- |
| M-FH01 | Missing Blender | Clear error, no viewer | | |
| M-FH02 | Missing Startup.blend | Clear error | | |
| M-FH03 | Missing exportable_catalog.json | Instruction to rebuild catalog | | |
| M-FH04 | Blender timeout | Explicit failure | | |
| M-FH05 | Concurrent two exports | No corruption; both succeed or fail cleanly | | |

---

## 12. How to reproduce

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
| RAG | Recall@k, nDCG@k, claim support, hallucination, citation correctness, abstention, figure success | §10 + §2 |
| MCP | Catalog accuracy, verified export rate, viewer success, latency | §11 + §3 |
| System | Likert usability (optional) | §4 |

---

## Appendix A — Exploratory vs final summary table

| Dimension | Exploratory finding | Final metric to report |
| --------- | ------------------- | ---------------------- |
| Retrieval | Frequent wrong PDF pages for muscle/joint queries | Recall@k, source hit rate |
| Grounding | VOR answers well grounded; shoulder talk off-topic | Claim support rate |
| Abstention | Often correctly refuses when context empty | Correct abstention rate |
| Multimodal | VOR returned 2–3 figures | Figure retrieval success rate |
| Reliability | 1/8 German queries HTTP 500 | Error rate / uptime |
| MCP | (pending final run) | Verified export success rate |

---

## Appendix B — Related repository files

| File | Role |
| ---- | ---- |
| `docs/THESIS_SYSTEM_DESIGN_AND_MCP.md` | Dual-pipeline architecture and evolution |
| `src/multimodal/thesis_rag_eval.py` | Baseline vs strict RAG experiment |
| `src/multimodal/multimodal_rag_chain.py` | Production hybrid retrieval + citation cap |
| `anatomy_mcp/label_index/exportable_catalog.json` | Geometry-validated MCP catalog |
| `german_eval_results.json` | Exploratory German Q&A log |
| `scripts/run_thesis_batch.py` | Batch evaluation runner |
| `scripts/thesis_questions_sample.txt` | English sample questions |

---

*Document version: 1.0 — evaluation plan + exploratory Q&A + final workbook templates for thesis submission.*

# Thesis Master Resource - Chapter-by-Chapter Plan

Project: Design and Implementation of a Multimodal Anatomy Learning Assistant Using Retrieval-Augmented Generation and Model Context Protocol-Based 3D Visualization
Author: Adarsh Raj
Last updated: 2026-07-06

## 1. How this resource should be used

Use this file as the main project knowledge resource when creating each thesis chapter in a separate chat. Each chapter chat should start by pasting the corresponding chapter prompt from `chapter_prompts/` or `project_resources/CHAPTER_CHAT_PROMPTS.md`.

The thesis should be written as an academic AI/ML engineering thesis. The strongest narrative is not only that a system was built, but that design alternatives were explored, problems were observed, and the architecture evolved into a clearer dual-pipeline system.

## 2. Supervisor requirement distilled from the email chain

The thesis must explicitly satisfy these requirements:

1. Document explored design options, the rationale behind them, the observations from trying them, and what was learned.
2. Focus less on claiming a perfect final product and more on the learning process: what worked, what did not, and why.
3. Include a literature survey on approaches and challenges for text, image, and possibly 3D outputs.
4. Start from a simple RAG approach and explain the expansion toward 2D image retrieval and 3D anatomy data.
5. Demonstrate feasibility and provide a qualitative evaluation.
6. Explain copyright/local deployment concerns clearly: HFU/anatomy material should remain local; object storage should be internal; persistent logs should be optional and mainly for evaluation.
7. Explain the RAG evaluation questions: confidence score, scoring method, citations, hallucination reasons, reference limit, passage ranking, answer synthesis, and model comparison.
8. Explain MCP/Blender reliability: whether the complete anatomy model can be searched, whether subsets are needed, and how incorrect exports such as the earlier left femur issue are handled.

## 3. Central thesis argument

The thesis contribution is a dual-pipeline architecture for anatomy education:

- Mode A: Document-grounded RAG Chatbot
  - Input: natural-language anatomy questions and uploaded PDFs.
  - Knowledge source: uploaded anatomy/course PDFs.
  - Techniques: PDF ingestion, chunking, MiniLM embeddings, Chroma, BM25/hybrid retrieval, CLIP image retrieval, evidence grading, answer synthesis, citation filtering.
  - Output: grounded text answer, up to three references, optional images.
  - Evaluation: retrieval quality, faithfulness, citation correctness, hallucination reduction, abstention behavior.

- Mode B: MCP 3D Anatomy
  - Input: anatomy structure names such as `left femur` or `Femur.l`.
  - Knowledge source: Z-Anatomy `Startup.blend` and geometry-validated `exportable_catalog.json`.
  - Techniques: Model Context Protocol, stdio tool server, FastMCP tools, Blender headless export, GLB generation, annotation JSON, Three.js viewer.
  - Output: 3D GLB model, annotations, viewer URL.
  - Evaluation: catalog match accuracy, export success, GLB generation, viewer loading, annotation availability, latency, cache behavior.

The two modes must remain separate in design and evaluation: RAG must not be judged by GLB export success, and MCP must not be judged by PDF citation quality.

## 4. Professor-driven research questions

RQ1. How effectively can a hybrid RAG pipeline provide grounded anatomy answers from uploaded PDFs?

RQ2. How does multimodal retrieval improve support for anatomy questions that require figures or visual context?

RQ3. How can MCP-based tool execution reduce unverifiable or fake 3D-generation claims compared with prompt-only or direct-function approaches?

RQ4. What design trade-offs and limitations arise in a local-first multimodal anatomy assistant for educational use?

## 5. Final thesis structure and writing order

Recommended writing order:

1. Chapter 3 - Requirements and System Design
2. Chapter 4 - Implementation
3. Chapter 5 - System Evolution and Design Decisions
4. Chapter 6 - Evaluation Methodology
5. Chapter 7 - Results and Discussion
6. Chapter 1 - Introduction
7. Chapter 2 - Related Work
8. Chapter 8 - Conclusion and Future Work
9. Abstract

## 6. Chapter-by-chapter plan

### Chapter 1 - Introduction

Purpose: Motivate the work and define the problem, objectives, contribution, and research questions.

Must prove:
- Anatomy learning requires text, images, and spatial understanding.
- General LLMs can hallucinate and cannot reliably cite local course material.
- A local-first document-grounded system is important for copyright-sensitive educational material.
- 3D visualization should not be fake text output; it should be a verifiable tool result.

Suggested sections:
1. Motivation
2. Problem Statement
3. Research Gap
4. Objectives
5. Research Questions
6. Contributions
7. Scope and Non-Goals
8. Thesis Structure

Evidence to cite/reference:
- Email chain: original thesis vision, simple RAG to 2D/3D, feasibility, qualitative evaluation.
- Project docs: dual-pipeline architecture, RAG and MCP mode separation.
- Screenshots: final UI with RAG answer and MCP viewer.

Still needed:
- Final screenshots.
- One paragraph clarifying that the system is an educational prototype and not clinical decision support.

### Chapter 2 - Background and Related Work

Purpose: Show that the design choices are grounded in existing AI/ML literature.

Must prove:
- RAG addresses LLM grounding and hallucination problems.
- Dense retrieval alone is not enough for exact anatomy terminology.
- BM25 and dense retrieval can be combined through hybrid retrieval or rank fusion.
- CLIP-style models support image-text retrieval.
- 3D anatomy visualization is educationally relevant.
- MCP/tool use is relevant for verifiable external actions.

Suggested sections:
1. LLMs in Education and Anatomy Learning
2. Hallucination and Grounding
3. Retrieval-Augmented Generation
4. Sparse, Dense, and Hybrid Retrieval
5. Multimodal Retrieval and CLIP
6. Evaluation of RAG Systems
7. 3D Anatomy Visualization
8. Tool-Using LLMs and Model Context Protocol
9. Positioning of This Thesis

Evidence/literature to cite:
- Lewis et al. 2020 RAG
- Karpukhin et al. 2020 DPR
- Robertson and Zaragoza BM25
- Cormack et al. 2009 RRF
- Reimers and Gurevych Sentence-BERT
- Radford et al. 2021 CLIP
- RAGAS paper
- Hallucination survey
- 3D anatomy education studies
- Official MCP documentation/specification

Still needed:
- Verify final references in `references_manual.tex`.
- Add any required German university citation style adjustments.

### Chapter 3 - Requirements and System Design

Purpose: Explain what the system must do and how the final architecture satisfies the requirements.

Must prove:
- The system has two separate modes.
- Each mode has its own inputs, knowledge source, processing pipeline, outputs, and evaluation criteria.
- The separation directly answers supervisor concerns about grounding, source attribution, local data handling, and 3D reliability.

Suggested sections:
1. Design Goals
2. Functional Requirements
3. Non-Functional Requirements
4. Dual-Pipeline Architecture
5. Mode A: RAG Chatbot
6. Mode B: MCP 3D Anatomy
7. Data and Storage Design
8. Failure Handling and Verification
9. Evaluation Separation

Evidence to cite/reference:
- `PROJECT_SUMMARY.md`
- `ARCHITECTURE_FOR_DIAGRAMS.md`
- `THESIS_SYSTEM_DESIGN_AND_MCP.md`
- Email chain: local/copyright concerns and final MCP separation.

Still needed:
- Architecture diagram exported as PDF/PNG.
- Screenshot of system UI with both panels.

### Chapter 4 - Implementation

Purpose: Explain how the architecture was built in code.

Must prove:
- The implementation maps clearly to the system design.
- Routes, services, retrieval components, storage, MCP server, Blender export, and frontend are traceable to code files.

Suggested sections:
1. Repository Structure
2. FastAPI Backend
3. PDF Ingestion Pipeline
4. Text Retrieval Pipeline
5. Multimodal Image Retrieval
6. RAG Answer Generation
7. Object Storage and URL Handling
8. MCP Client and Tool Server
9. Blender/Z-Anatomy Export Pipeline
10. Frontend Integration
11. Configuration and Reproducibility

Code files to reference:
- `app/main.py`
- `app/services/rag_service.py`
- `app/services/ingestion_service.py`
- `app/services/object_storage.py`
- `src/ingestion/run.py`
- `src/retrieval/hybrid_retriever.py`
- `src/multimodal/multimodal_rag_chain.py`
- `src/multimodal/multimodal_retriever.py`
- `app/services/anatomy_mcp_chat.py`
- `app/services/anatomy_mcp_client.py`
- `anatomy_mcp/server.py`
- `anatomy_mcp/label_index/exportable_catalog.json`
- `frontend/app/components/AnatomyMcpPanel.js`

Still needed:
- Freeze commit hash.
- Record exact environment: Python, Node, Blender, LM Studio model.

### Chapter 5 - System Evolution and Design Decisions

Purpose: This is the most important chapter for Prof. Ziekow's requirement. It must explain what was tried, why, what happened, and how the system changed.

Must prove:
- The thesis is a learning-oriented engineering study, not just a final demo.
- Each important design decision came from an observed limitation.

Suggested sections:
1. Initial Monolithic RAG Prototype
2. Dense-Only Retrieval and Exact-Term Failures
3. Citation Sprawl and Source Duplication
4. Hallucination Under Weak Retrieval
5. Figure Blindness in Text-Only Retrieval
6. Fragile Local Image Paths and Storage Redesign
7. Procedural Blender and Fake 3D Success
8. Raw Label Matching versus Geometry-Proven Catalog
9. Direct Python Calls versus True MCP
10. RAG/MCP Coupling and Evaluation Separation
11. Lessons Learned

Use a recurring pattern:
- Design tried
- Rationale
- Observation
- Problem
- Correction
- Lesson learned

Key thesis table:
| Design option | Rationale | Observation | Correction | Lesson |

Still needed:
- Screenshots/logs of failure cases if available.
- Short code snippets or JSON responses showing fake/failed export prevention.

### Chapter 6 - Evaluation Methodology

Purpose: Define how the system will be evaluated. This chapter should not invent results.

Must prove:
- Evaluation follows the two-mode architecture.
- RAG evaluation tests retrieval, grounding, citation quality, hallucination, and abstention.
- MCP evaluation tests catalog resolution, export success, viewer loading, and safe failure.

Suggested sections:
1. Evaluation Goals
2. Evaluation Dataset
3. RAG Evaluation Protocol
4. RAG Metrics
5. RAG Ablation Studies
6. MCP Evaluation Protocol
7. MCP Metrics
8. Failure and Boundary Tests
9. Limitations of the Evaluation

Use existing Excel files:
- `hfu_anatomy_rag_evaluation.xlsx`: initial RAG evaluation with 15 questions and metric categories.
- `chatbot_qa_quality_comparison.xlsx`: document-only QA comparison, overall quality around 3.5/10 in that early evaluation.
- `DOC-20260629-WA0016..xlsx`: Qwen/Gemma/ChatGPT comparison and model behavior observations.

Still needed:
- Final run on frozen code.
- Decide whether to report early exploratory results separately from final evaluation.

### Chapter 7 - Results and Discussion

Purpose: Present measured results and explain them honestly.

Must prove:
- Improvements are visible in retrieval/citation behavior, but limitations remain.
- Model choice matters, but pipeline quality matters more.
- MCP gives more verifiable 3D behavior than prompt-only claims.

Suggested sections:
1. RAG Results
2. Model Comparison Results
3. MCP Results
4. Failure Case Analysis
5. Discussion of Design Trade-Offs
6. Threats to Validity
7. Summary of Findings per Research Question

Use cautious wording:
- Do not claim medical correctness.
- Do not claim production readiness.
- Distinguish early exploratory evaluation from final frozen-system evaluation.

Still needed:
- Final metric tables.
- Final screenshots.
- Any latency and cache measurements.

### Chapter 8 - Conclusion and Future Work

Purpose: Close the thesis by summarizing contributions, limitations, and future work.

Must prove:
- The final prototype demonstrates feasibility.
- The learning story and architecture separation are the main research outcome.
- The limitations are understood and do not overclaim.

Suggested sections:
1. Summary
2. Answers to Research Questions
3. Contributions
4. Limitations
5. Future Work
6. Final Reflection

Future work:
- OCR for figure text.
- Larger gold dataset.
- Automated RAG evaluation with RAGAS/TruLens.
- Entity linking between RAG answer and MCP viewer.
- Better frontend UX.
- Larger student/user study.
- Cloud/local deployment hardening.

Still needed:
- Final exact contribution list from completed experiments.

## 7. Chapter chat workflow

For each new chat in this project:

1. Start the chat title as `Chapter X - <chapter name>`.
2. Paste the matching prompt from `CHAPTER_CHAT_PROMPTS.md`.
3. Ask for one of these outputs:
   - chapter plan only;
   - polished section draft;
   - improve existing draft;
   - add citations and evidence notes;
   - convert bullets to academic prose;
   - create table/figure text;
   - create experiment/result narrative.
4. Always request these five outputs:
   - what the section must prove;
   - thesis-ready draft;
   - table/diagram suggestion;
   - evidence/code files to cite;
   - missing data/screenshot/metric.

## 8. Minimum evidence checklist before final submission

- Frozen repository commit hash.
- Setup commands tested from clean environment.
- Screenshot: PDF upload.
- Screenshot: RAG answer with citations.
- Screenshot: RAG insufficient-evidence/refusal case.
- Screenshot: image retrieval case.
- Screenshot: MCP 3D viewer loaded.
- Screenshot/API JSON: MCP failure case with no fake viewer.
- RAG evaluation table.
- MCP evaluation table.
- Model comparison table.
- Discussion of local deployment/copyright handling.
- Discussion of limitations.

## 9. Style rules

- Academic English.
- Honest, cautious claims.
- Use `prototype`, `implementation`, `evaluation`, and `future work` precisely.
- Do not claim clinical decision support.
- Do not invent final numbers.
- Separate early exploratory evaluation from final frozen-system evaluation.
- Keep RAG and MCP separate in evaluation.

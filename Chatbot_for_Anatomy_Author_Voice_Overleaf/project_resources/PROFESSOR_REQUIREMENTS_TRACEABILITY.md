# Professor Requirements Traceability Matrix

This matrix translates the email-chain guidance into thesis chapters, evidence, and writing actions.

| Supervisor requirement / concern | Source in email chain | Thesis response | Main chapter(s) | Evidence to include |
|---|---|---|---|---|
| Document explored design options, rationale, observations, and learning | Prof. Ziekow feedback, 9 June 2026 | Make Chapter 5 the core learning narrative, with design-option tables | Ch. 5, Ch. 7 | Design evolution table, failure/correction screenshots, code references |
| Thesis is more about learning what works and what does not than only final solution | Prof. Ziekow feedback, 9 June 2026 | Frame thesis as design/implementation/evaluation study, not product report | Ch. 1, Ch. 5, Ch. 8 | Research questions, contribution statement, lessons learned |
| Literature survey on approaches/challenges | Meeting notes, 12 Feb 2026 | Cover RAG, hallucination, hybrid retrieval, multimodal retrieval, 3D anatomy, MCP | Ch. 2 | Literature review table |
| Start with simple RAG and expand toward 2D/3D anatomy data | Meeting notes, 12 Feb 2026 | Explain v0 simple RAG then CLIP/image and MCP/Blender evolution | Ch. 3, Ch. 5 | Architecture evolution diagram |
| Demonstrate feasibility and qualitative evaluation | Meeting notes, 12 Feb 2026 | Evaluate prototype qualitatively and quantitatively where available | Ch. 6, Ch. 7 | RAG and MCP evaluation tables |
| Local-first/copyright concerns | Prof. Heermann questions, 24 Feb 2026 | Explain Hugging Face as dev only, final concept local; MinIO/local storage; optional logs | Ch. 3, Ch. 4, Ch. 8 | Storage design, reproducibility checklist |
| Clarify image retrieval and image output behavior | April feedback and implementation updates | Explain extracted figures, dynamic 0-3 images, storage URLs, no arbitrary image generation | Ch. 3, Ch. 4, Ch. 5 | UI screenshots and API JSON |
| Avoid generating 3D models from scratch; use existing anatomy assets | April feedback | Explain rejection of procedural Blender as final path; use Z-Anatomy and exportable catalog | Ch. 5 | MCP architecture, catalog/export screenshots |
| Explain confidence score and manual scoring | Prof. Heermann questions, 3 June 2026 | Describe as custom/evaluation score, not medical correctness | Ch. 6, Ch. 7 | Scoring rubric tables |
| Explain model comparison and fixed model issue | Prof. Heermann questions, 3 June 2026 | State early ChatGPT comparison was informal unless model fixed; final evaluation should freeze model versions | Ch. 6, Ch. 7 | Model comparison table, environment table |
| Explain citations and whether they come from PDF | Prof. Heermann questions, 3 June 2026 | Explain citation/source pipeline and citation quality metric | Ch. 4, Ch. 6, Ch. 7 | API response with source cards |
| Test local small LLM | Prof. Heermann questions, 3 June 2026 | Include Qwen/Gemma/local model comparison if reproduced; otherwise mark as exploratory | Ch. 6, Ch. 7 | DOC-20260629-WA0016..xlsx |
| Explain hallucination reasons | Prof. Heermann questions, 3 June 2026 | Connect hallucination to weak retrieval, weak filtering, unsupported synthesis | Ch. 5, Ch. 7 | Failure examples |
| Explain why maximum three references | Prof. Heermann questions, 3 June 2026 | Explain UI/design readability plus retrieval internals; evaluate citation quality not quantity | Ch. 3, Ch. 4, Ch. 6 | Source filtering code and UI screenshot |
| Explain passage importance and synthesis | Prof. Heermann questions, 3 June 2026 | Explain hybrid retrieval, reranking, evidence grading, LLM synthesis limitations | Ch. 4, Ch. 5 | Retrieval pipeline diagram |
| Left femur export looked incorrect; test more structures | Prof. Heermann questions, 3 June 2026 | Include MCP evaluation with exact labels, natural language names, left/right structures, ambiguous terms | Ch. 6, Ch. 7 | MCP test table and screenshots |
| Clear separation between RAG and MCP | Update email, 2 June 2026 | Explain separate UI panels, endpoints, knowledge sources, and evaluation metrics | Ch. 3, Ch. 4, Ch. 6 | Architecture diagram |

## Required thesis stance

Write the thesis as a careful prototype study:

- Correct phrase: `The prototype demonstrates feasibility...`
- Avoid: `The system guarantees correct medical answers...`
- Correct phrase: `The evaluation suggests...`
- Avoid: `The system is fully production-ready...`
- Correct phrase: `The score is an evaluation rubric score, not a clinical correctness score.`
- Avoid: `The confidence score proves answer correctness.`

## Chapter 5 table template

| Phase | Design tried | Rationale | Observation | Correction | Lesson learned |
|---|---|---|---|---|---|
| v0 | Dense-only RAG | Fast baseline | Exact anatomy terms were missed | Hybrid BM25 + dense retrieval | Anatomy needs lexical and semantic retrieval |
| v1 | Text-only retrieval | Simpler implementation | Figure-related questions failed | CLIP multimodal retrieval | Anatomy learning is visual |
| v2 | Local image paths | Simple development | Deployed URLs broke | Storage abstraction | Retrieval metadata must be serveable |
| v3 | Procedural Blender | Quick demo | Not anatomy-source grounded | Z-Anatomy export | 3D output must be from real assets |
| v4 | Direct Python calls | Fast integration | Not proper MCP | MCP stdio tool server | Tool execution should be auditable |
| final | Dual pipeline | Evaluation clarity | RAG and MCP separable | Independent metrics | Different outputs require different evaluation |

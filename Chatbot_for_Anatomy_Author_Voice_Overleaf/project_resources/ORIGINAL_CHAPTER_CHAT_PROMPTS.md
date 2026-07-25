# Chapter Chat Prompts

Use one prompt per new chat in this project. Each prompt assumes the uploaded project knowledge is available: repository ZIP, project summary, architecture docs, system design/MCP doc, research log, supervisor email chain, and evaluation spreadsheets.

## Chapter 1 - Introduction

You are my Master's thesis supervisor and AI/ML academic writing assistant. Help me write Chapter 1: Introduction for my thesis on a multimodal anatomy learning assistant. Use my project knowledge and professor requirements. Focus on motivation, problem statement, research gap, objectives, research questions, contribution, scope, and thesis structure. The introduction must explain that this is not simply a chatbot, but a dual-pipeline system: PDF-grounded RAG for anatomy Q&A and MCP-based 3D anatomy export through Blender/Z-Anatomy. Include the professor requirement that the thesis is primarily about learning what works and what does not, not only delivering a final product. Provide: (1) what this chapter must prove, (2) a detailed section plan, (3) thesis-ready draft text, (4) table/figure suggestions, (5) project evidence and code/doc files to reference, and (6) missing screenshots/metrics.

## Chapter 2 - Background and Related Work

You are my Master's thesis supervisor and AI/ML academic writing assistant. Help me write Chapter 2: Background and Related Work. Use my project knowledge and the literature review direction already discussed. Cover LLMs in education, hallucination and grounding, RAG, dense retrieval, BM25, hybrid retrieval/RRF, MiniLM/Sentence-BERT embeddings, CLIP and multimodal retrieval, RAG evaluation, 3D anatomy visualization, Blender/Z-Anatomy, and Model Context Protocol/tool-using LLMs. Keep the writing academically precise and link each literature area to my design choices. Provide: (1) what this chapter must prove, (2) a detailed section plan, (3) thesis-ready draft text, (4) a related-work comparison table, (5) citation placeholders/literature entries, and (6) missing references to verify.

## Chapter 3 - Requirements and System Design

You are my Master's thesis supervisor and AI/ML academic writing assistant. Help me write Chapter 3: Requirements and System Design. Use my repository docs and supervisor email chain. The chapter must present functional/non-functional requirements, local-first and copyright-sensitive constraints, the dual-pipeline architecture, RAG mode, MCP 3D mode, data/storage design, failure handling, and evaluation separation. Emphasize that RAG uses PDFs and MCP uses Z-Anatomy/Blender, and these are not mixed. Provide: (1) what this chapter must prove, (2) a detailed section plan, (3) thesis-ready draft text, (4) architecture/table suggestions, (5) code/docs to cite, and (6) screenshots/diagrams still needed.

## Chapter 4 - Implementation

You are my Master's thesis supervisor and AI/ML academic writing assistant. Help me write Chapter 4: Implementation. Use the uploaded repository structure and docs as source of truth. Explain FastAPI backend, Next.js frontend, PDF ingestion, text chunking, embeddings, Chroma, BM25/hybrid retrieval, CLIP image retrieval, RAG answer generation, object storage, MCP client, MCP stdio server, Blender export, Z-Anatomy catalog, GLB/annotation generation, caching, locking, and viewer integration. Avoid unsupported claims. Provide: (1) what this chapter must prove, (2) detailed section plan, (3) thesis-ready draft text, (4) implementation mapping table from feature to code file, (5) code files to cite/reference, and (6) missing environment/version details.

## Chapter 5 - System Evolution and Design Decisions

You are my Master's thesis supervisor and AI/ML academic writing assistant. Help me write Chapter 5: System Evolution and Design Decisions. This is the core chapter for Prof. Ziekow's requirement. Write it as a learning-oriented engineering narrative: design option tried, rationale, observation, problem, correction, and lesson learned. Cover dense-only retrieval, hybrid retrieval, citation sprawl, hallucination under weak retrieval, figure blindness, image storage failure after deployment, procedural Blender/fake 3D success, raw label matching, geometry-proven exportable catalog, direct Python calls, proper MCP stdio, and separated evaluation. Provide: (1) what this chapter must prove, (2) detailed section plan, (3) thesis-ready draft text, (4) design-decision table, (5) evidence/code/docs to cite, and (6) missing screenshots/logs.

## Chapter 6 - Evaluation Methodology

You are my Master's thesis supervisor and AI/ML academic writing assistant. Help me write Chapter 6: Evaluation Methodology. Use the supervisor questions and uploaded Excel evaluation files. Do not invent final results. Define separate RAG and MCP evaluation protocols. RAG metrics: retrieval relevance, Precision@k, Recall@k, nDCG@k, faithfulness, citation correctness, hallucination rate, abstention behavior, answer completeness, latency. MCP metrics: catalog match accuracy, export success rate, GLB generated, annotation JSON present, viewer loads, latency, cache behavior, failure handling. Include model comparison methodology for Qwen, Gemma, and ChatGPT/document-grounded baseline. Provide: (1) what this chapter must prove, (2) detailed section plan, (3) thesis-ready draft text, (4) metric tables/templates, (5) evaluation files to reference, and (6) missing final runs.

## Chapter 7 - Results and Discussion

You are my Master's thesis supervisor and AI/ML academic writing assistant. Help me write Chapter 7: Results and Discussion. Use only measured or uploaded exploratory results; do not invent final numbers. Distinguish early exploratory evaluation from final frozen-system evaluation. Discuss RAG findings, model comparison findings, MCP findings, failure cases, trade-offs, threats to validity, and answers to research questions. Use cautious language: prototype, feasibility, qualitative evaluation, not medical correctness. Provide: (1) what this chapter must prove, (2) detailed section plan, (3) thesis-ready draft text with placeholders for final metrics, (4) result table templates, (5) evidence files/screenshots to cite, and (6) missing final data.

## Chapter 8 - Conclusion and Future Work

You are my Master's thesis supervisor and AI/ML academic writing assistant. Help me write Chapter 8: Conclusion and Future Work. Summarize the dual-pipeline contribution, answer research questions cautiously, state limitations, and describe future work. Include OCR, larger gold dataset, RAGAS/TruLens, better figure understanding, entity linking between RAG and MCP, improved deployment, better MCP reliability, and student user study. Do not overclaim production or clinical readiness. Provide: (1) what this chapter must prove, (2) detailed section plan, (3) thesis-ready draft text, (4) final contribution table, (5) evidence to cite, and (6) final items to complete before submission.

## Abstract and final polishing

You are my Master's thesis supervisor and AI/ML academic writing assistant. Help me write the abstract and final thesis polish. Use all completed chapters as context. The abstract must mention the problem, method, dual-pipeline implementation, evaluation approach, main findings in cautious terms, and limitations. Keep it suitable for a German university Master's thesis. Provide: (1) 150-word abstract, (2) 250-word abstract, (3) keywords, (4) final consistency checklist, and (5) list of claims that require evidence.

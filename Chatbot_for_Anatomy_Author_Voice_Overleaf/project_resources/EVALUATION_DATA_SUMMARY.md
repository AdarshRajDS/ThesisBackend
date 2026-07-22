# Evaluation Data Summary from Uploaded Excel Files

This file summarizes the uploaded evaluation spreadsheets so that each chapter chat can reuse the evaluation material without reopening the Excel files.

## 1. `hfu_anatomy_rag_evaluation.xlsx`

Sheets:
- `RAG Evaluation`
- `Scoring Method`
- `Summary`

Important summary values from the workbook:
- Total test questions: 15
- Pass: 10
- Pass with caveat: 2
- Needs review: 1
- Fail: 2
- Average validity score: 4.20
- Average accuracy score: 4.47
- Average completeness score: 4.13
- Average grounding score: 3.87
- Average citation quality score: 3.47
- Average boundary handling score: 4.80

Main strengths recorded:
- Good grounded answers for core anatomy questions.
- Correct out-of-context consent behavior.
- Strong synthesis for some pathway-style questions.

Main weaknesses recorded:
- Unsupported exact quote behavior.
- Weak typo recovery.
- Irrelevant citations for some figure or broad answers.
- Weak external references after consent.

Recommended priority fixes recorded:
1. Quote verification.
2. Typo/query rewriting.
3. Citation relevance filtering.
4. Better external citation policy after consent.

How to use in thesis:
- Chapter 6: describe this as an early/manual evaluation rubric.
- Chapter 7: present as exploratory evaluation unless re-run on the frozen final system.
- Chapter 5: use failures to justify stricter grounding and better citation filtering.

## 2. `chatbot_qa_quality_comparison.xlsx`

Sheets:
- `QA Comparison`
- `Summary`

Important summary values:
- Overall quality: 3.5/10 in the early document-only comparison.
- Best answer: shoulder-girdle short talk, because it was structured and mostly grounded.
- Worst answers: hip flexor and ankle muscles, because the system used unrelated evidence and invented unsupported content.
- Main issue: unsupported generation from weak snippets.
- Suggested correction: every answer sentence should be supported by a cited passage, and weak retrieval should lead to an insufficient-evidence response.

How to use in thesis:
- Chapter 5: evidence for the hallucination-under-weak-retrieval problem.
- Chapter 6: basis for rubric dimensions such as grounding, citation quality, and boundary handling.
- Chapter 7: early baseline/exploratory result, not final system performance unless reproduced.

## 3. `DOC-20260629-WA0016..xlsx`

Sheets:
- `Summary`
- `Comparison`
- `Raw Answers`
- `Rubric`
- `Source Notes`

Important model-comparison summary:
- Qwen average score: 2.56
- Gemma average score: 5.56
- ChatGPT/document-grounded baseline average score: 8.89
- Qwen strength: more complete synthesis when relevant passages are retrieved.
- Qwen weakness: more hallucination-prone when retrieval is weak.
- Gemma strength: more conservative and safer for strict document-only behavior.
- Gemma weakness: less complete when retrieval is poor; may answer `not found`.
- Main conclusion: model choice matters, but the larger issue is the full RAG pipeline: retrieval quality, reranking, passage filtering, grounding, citation relevance, and synthesis.

How to use in thesis:
- Chapter 6: model comparison protocol.
- Chapter 7: model comparison discussion.
- Chapter 5: justify the shift from focusing only on the LLM to improving retrieval, filtering, and grounding.

## 4. Important caution for writing

Do not present these values as final thesis results unless they are from the frozen final repository version and reproducible run. In the current thesis they can be described as:

- exploratory evaluation;
- manual rubric-based comparison;
- formative evaluation used to identify system weaknesses;
- evidence that the pipeline, not only model selection, controls answer quality.

## 5. Final evaluation still needed

Before final submission, run a clean evaluation on the frozen system:

- Use the same question set.
- Record model versions and configuration.
- Save raw responses.
- Score with a fixed rubric.
- Separate RAG and MCP results.
- Add screenshots and API JSON evidence.

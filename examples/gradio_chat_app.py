"""
Reference Gradio UI aligned with ThesisBackend APIs.

Copy into your Space / frontend repo. Env vars:
  BACKEND_URL          default http://127.0.0.1:8000
  USE_EXPERIMENT_RAG   true|false — experiment = /rag/experiment/ask (full analysis)
  CHAT_ANSWER_MODE     coherent|strict|baseline — only when USE_EXPERIMENT_RAG=true
  THESIS_PERSIST_LOG   true|false — append experiment runs to thesis_rag_eval.jsonl
"""

import os

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"

import gradio as gr
import requests

# =============================
# BACKEND CONFIG
# =============================

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

USE_EXPERIMENT_RAG = os.getenv("USE_EXPERIMENT_RAG", "true").lower() in (
    "true",
    "1",
    "yes",
)

# coherent | strict | baseline (only used when calling /rag/experiment/ask)
CHAT_ANSWER_MODE = os.getenv("CHAT_ANSWER_MODE", "coherent").lower()

THESIS_PERSIST_LOG = os.getenv("THESIS_PERSIST_LOG", "false").lower() in (
    "true",
    "1",
    "yes",
)

RAG_URL_PRODUCTION = f"{BACKEND_URL}/rag/ask"
RAG_URL_EXPERIMENT = f"{BACKEND_URL}/rag/experiment/ask"

UPLOAD_URL = f"{BACKEND_URL}/upload-pdf/"
VISUALIZE_URL = f"{BACKEND_URL}/visualize/"
GRADE_URL = f"{BACKEND_URL}/grade-annotation/"

# =============================
# GLOBAL STATE
# =============================

last_response = None


def _chat_answer_from_payload(data: dict) -> str:
    """Pick main chat text from backend JSON."""
    if USE_EXPERIMENT_RAG:
        if CHAT_ANSWER_MODE == "baseline":
            return data.get("baseline_answer") or "⚠️ No answer returned."
        if CHAT_ANSWER_MODE == "strict":
            return data.get("strict_rag_answer") or "⚠️ No answer returned."
        # coherent (default)
        return (
            data.get("strict_rag_coherent")
            or data.get("strict_rag_answer")
            or data.get("baseline_answer")
            or "⚠️ No answer returned."
        )
    return data.get("answer") or "⚠️ No answer returned."


def _scores_markdown_baseline_vs_strict(evaluation: dict) -> str:
    """
    Map faithfulness_a / _b to Baseline vs Strict using evaluation.presentation.
    """
    pres = evaluation.get("presentation") or {}
    scores = evaluation.get("scores") or {}
    if not pres or "A" not in pres or "B" not in pres:
        return "_No presentation map (A/B labels) in evaluation._\n"

    # Map score suffix _a / _b to baseline vs strict_rag
    def get_baseline_strict():
        if pres["A"] == "baseline" and pres["B"] == "strict_rag":
            return "a", "b"
        if pres["A"] == "strict_rag" and pres["B"] == "baseline":
            return "b", "a"
        return None, None

    b_suffix, s_suffix = get_baseline_strict()
    if not b_suffix:
        return f"_Unexpected presentation: {pres}_\n"

    def pick(metric_prefix: str):
        return (
            scores.get(f"{metric_prefix}_{b_suffix}"),
            scores.get(f"{metric_prefix}_{s_suffix}"),
        )

    rows = [
        ("Faithfulness", pick("faithfulness")),
        ("Relevance", pick("relevance")),
        ("Completeness", pick("completeness")),
        ("Clarity", pick("clarity")),
    ]

    lines = [
        "| Metric | Baseline (no docs in prompt) | Strict RAG (context-only arm) |",
        "|--------|------------------------------|-------------------------------|",
    ]
    for name, (bv, sv) in rows:
        lines.append(f"| {name} | {bv} | {sv} |")
    return "\n".join(lines) + "\n"


def _sources_markdown(sources: list) -> str:
    if not sources:
        return "_No sources retrieved._\n"
    parts = []
    for i, s in enumerate(sources, 1):
        src = s.get("source") or "?"
        page = s.get("page")
        preview = (s.get("chunk_preview") or "").strip()
        parts.append(f"**[{i}] {src} (Page {page})**\n\n")
        if preview:
            parts.append(f"> {preview}\n\n")
    return "".join(parts)


def _render_3d_markdown(data: dict) -> str:
    parts = []
    anatomy = data.get("render_3d_anatomy")
    image_url = data.get("render_3d_url")
    model_url = data.get("render_3d_model_url")

    if image_url:
        parts.append(f"\n\n### 3D anatomy render ({anatomy or 'detected'})")
        parts.append(f"\n\n![3D anatomy render]({image_url})")
    if model_url:
        parts.append("\n\n### Interactive 3D model")
        parts.append(f"\n\n[Open GLB model in browser/viewer]({model_url})")
    return "".join(parts)


# =============================
# RAG CHAT
# =============================


def ask_question(message, history):
    global last_response

    if history is None:
        history = []

    url = RAG_URL_EXPERIMENT if USE_EXPERIMENT_RAG else RAG_URL_PRODUCTION
    payload: dict = {"question": message}
    if USE_EXPERIMENT_RAG:
        payload["persist_log"] = THESIS_PERSIST_LOG

    try:
        r = requests.post(url, json=payload, timeout=600)
        r.raise_for_status()
        data = r.json()
        print("Backend response keys:", list(data.keys()))

        last_response = data

        answer = _chat_answer_from_payload(data)

        images_md = ""
        for img in data.get("images") or []:
            images_md += f"\n\n![image]({img})"
        render_3d_md = _render_3d_markdown(data)

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": answer + images_md + render_3d_md})

        analysis_visible = bool(USE_EXPERIMENT_RAG)
        return "", history, gr.update(visible=analysis_visible)

    except Exception as e:
        print(f"Error in ask_question: {e}")
        history.append({"role": "assistant", "content": f"❌ Error: {str(e)}"})
        return "", history, gr.update(visible=False)


# =============================
# ANALYSIS PANEL
# =============================


def format_analysis() -> str:
    global last_response

    if not last_response:
        return "⚠️ No analysis available yet. Ask a question first."

    d = last_response

    if not USE_EXPERIMENT_RAG:
        g = d.get("grounding") or {}
        src_md = _sources_markdown(d.get("sources") or [])
        render_md = _render_3d_markdown(d)
        return f"""## Production RAG (`/rag/ask`)

### Answer shown in chat

{d.get("answer", "N/A")}

### Grounding (heuristic)

- **primary_basis:** `{g.get("primary_basis", "N/A")}`
- **had_retrieved_passages_in_prompt:** {g.get("had_retrieved_passages_in_prompt", "N/A")}
- **unique_text_passages_used:** {g.get("unique_text_passages_used", "N/A")}
- **used_multimodal_text_excerpts:** {g.get("used_multimodal_text_excerpts", "N/A")}

**Provenance:** {g.get("provenance_explanation", "N/A")}

**Evaluation note:** {g.get("evaluation_note", "N/A")}

### Retrieved sources

{src_md}

### 3D output

{render_md if render_md else "_No related 3D render for this answer._"}
"""

    evaluation = d.get("evaluation") or {}
    winner = evaluation.get("winner_label") or evaluation.get("raw_winner") or "N/A"
    confidence = evaluation.get("confidence", "N/A")
    reasoning = evaluation.get("reasoning", "N/A")
    pres = evaluation.get("presentation") or {}

    scores_table = _scores_markdown_baseline_vs_strict(evaluation)

    strict_txt = d.get("strict_rag_answer", "N/A")
    coherent_txt = d.get("strict_rag_coherent", "N/A")
    baseline_txt = d.get("baseline_answer", "N/A")
    shown = _chat_answer_from_payload(d)

    dbg = d.get("debug") or {}

    return f"""## Thesis experiment (`/rag/experiment/ask`)

### Evaluation (judge: baseline vs **strict** RAG only)

**Winner:** `{winner}`  
**Confidence:** {confidence}

**Presentation (blind A/B):** A = `{pres.get("A", "?")}`, B = `{pres.get("B", "?")}`

{scores_table}

**Reasoning:**  
> {reasoning}

---

### Answer shown in chat (mode: `{CHAT_ANSWER_MODE}`)

{shown}

---

### Baseline (no retrieved context in that call)

{baseline_txt}

---

### Strict RAG (context-only, conservative)

{strict_txt}

---

### Coherent RAG (synthesis, same passages + citations)

{coherent_txt}

---

### Retrieved sources

{_sources_markdown(d.get("sources") or [])}

---

### Debug

- **presentation_order_rag_first:** {dbg.get("presentation_order_rag_first", "N/A")}
- **latency_ms:** {dbg.get("latency_ms", "N/A")}
- **num_sources:** {dbg.get("num_sources", "N/A")}
- **num_numbered_passages:** {dbg.get("num_numbered_passages", "N/A")}
- **had_retrieved_passages:** {dbg.get("had_retrieved_passages", "N/A")}

"""


def toggle_analysis():
    global last_response

    if not last_response:
        return gr.update(visible=False), "⚠️ No analysis available yet."

    if not USE_EXPERIMENT_RAG:
        return gr.update(visible=True), format_analysis()

    return gr.update(visible=True), format_analysis()


def hide_analysis():
    return gr.update(visible=False)


# =============================
# MINIMAL APP SKELETON (wire your own Blocks)
# =============================
#
# with gr.Blocks() as demo:
#     chatbot = gr.Chatbot(type="messages")
#     msg = gr.Textbox()
#     analysis = gr.Markdown(visible=False)
#     show_btn = gr.Button("Analysis", visible=False)
#
#     msg.submit(ask_question, [msg, chatbot], [msg, chatbot, show_btn])
#     show_btn.click(toggle_analysis, outputs=[analysis, analysis])  # adjust to your layout
#
# demo.launch()

if __name__ == "__main__":
    print("This file is a reference — import functions into your Gradio app or copy them.")
    print(f"BACKEND_URL={BACKEND_URL} USE_EXPERIMENT_RAG={USE_EXPERIMENT_RAG}")

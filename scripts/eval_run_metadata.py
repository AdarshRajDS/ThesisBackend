#!/usr/bin/env python3
"""Shared LLM / experiment metadata for evaluationThesis.md builders."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUNS_JSON = REPO / "eval" / "experiment_runs.json"


def load_runs() -> dict:
    return json.loads(RUNS_JSON.read_text(encoding="utf-8"))


def fetch_live_llm_snapshot(base_url: str = "http://127.0.0.1:8000") -> dict | None:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/debug/llm", timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def resolve_model_block(run_key: str, json_meta: dict | None = None) -> dict:
    """Merge static run config with optional per-run JSON meta and live snapshot."""
    runs = load_runs()
    cfg = dict(runs.get(run_key, {}))
    if json_meta:
        for k in ("llm_provider", "model_configured", "models_loaded_observed", "model_note", "api_base"):
            if json_meta.get(k) is not None:
                cfg[k] = json_meta[k]

    if not cfg.get("model_configured"):
        cfg["model_configured"] = os.getenv("LLM_MODEL", "google/gemma-4-e2b")

    provider = str(cfg.get("llm_provider", "")).lower()
    if provider in ("lmstudio", "local", "openai_compatible", "ollama"):
        live = fetch_live_llm_snapshot()
        if live:
            if live.get("model"):
                cfg.setdefault("model_configured", live["model"])
            if live.get("lmstudio_models"):
                cfg.setdefault("models_loaded_observed", live["lmstudio_models"])

    return cfg


def format_model_header(cfg: dict) -> str:
    lines = [
        f"**LLM provider:** {cfg.get('llm_provider', 'unknown')}",
        f"**Model (configured):** `{cfg.get('model_configured', 'unknown')}`",
    ]
    observed = cfg.get("models_loaded_observed")
    provider = str(cfg.get("llm_provider", "")).lower()
    if observed and provider in ("lmstudio", "local", "openai_compatible", "ollama"):
        if isinstance(observed, list):
            obs = ", ".join(f"`{m}`" for m in observed)
        else:
            obs = str(observed)
        lines.append(f"**Models loaded (observed):** {obs}")
    if cfg.get("model_note"):
        lines.append(f"**Model note:** {cfg['model_note']}")
    prev = cfg.get("model_previous")
    if prev:
        lines.append(f"**Model (previous):** `{prev}`")
    if cfg.get("api_base"):
        lines.append(f"**API base:** {cfg['api_base']}")
    if cfg.get("endpoint"):
        lines.append(f"**Endpoint:** `{cfg.get('endpoint')}`")
    if cfg.get("language"):
        lines.append(f"**Language:** `{cfg.get('language')}`")
    return "\n\n".join(lines)


def format_model_short(cfg: dict) -> str:
    model = cfg.get("model_configured") or "unknown"
    provider = cfg.get("llm_provider") or "unknown"
    return f"{provider} / `{model}`"


def build_experiment_registry_table() -> str:
    runs = load_runs()
    lines = [
        "## 9.0 Experiment runs and models",
        "",
        "Reference for all RAG evaluation batches in this document. Update `eval/experiment_runs.json` when you change model or provider.",
        "",
        "| Run | Section | Provider | Model (configured) | Language | Results file |",
        "| --- | ------- | -------- | ------------------ | -------- | ------------ |",
    ]
    for key, cfg in runs.items():
        model = cfg.get("model_configured", "—")
        lines.append(
            f"| {cfg.get('label', key)} | §{cfg.get('section', '?')} | "
            f"{cfg.get('llm_provider', '—')} | `{model}` | "
            f"{cfg.get('language', '—')} | `{cfg.get('json_file', '—')}` |"
        )
    lines.extend(["", "---", ""])
    return "\n".join(lines)


def merge_run_meta(run_key: str, existing: dict | None = None) -> dict:
    """Build meta dict to store alongside eval JSON results."""
    cfg = resolve_model_block(run_key, existing)
    meta = dict(existing or {})
    meta.update(
        {
            "llm_provider": cfg.get("llm_provider"),
            "model_configured": cfg.get("model_configured"),
            "models_loaded_observed": cfg.get("models_loaded_observed"),
            "api_base": cfg.get("api_base"),
        }
    )
    return meta

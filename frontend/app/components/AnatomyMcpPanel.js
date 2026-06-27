"use client";

import { useState } from "react";
import { Box, Send, Loader2, RefreshCw } from "lucide-react";
import AnatomyExportPanel from "./AnatomyExportPanel";
import { t } from "../i18n/strings";

const EXPORT_URL_RE = /https?:\/\/[^\s)\]"']+/gi;

function buildViewerUrl(apiBase, modelUrl, annotationsUrl) {
  if (!modelUrl || !annotationsUrl) return null;
  const origin = (apiBase || "http://127.0.0.1:8000").replace(/\/+$/, "");
  return `${origin}/anatomy-viewer/index.html?model=${encodeURIComponent(modelUrl)}&annotations=${encodeURIComponent(annotationsUrl)}`;
}

function salvageExportFromAnswer(answer, partQuery, apiBase) {
  if (!answer || !/anatomy-exports/i.test(answer)) return null;

  const urls = [
    ...new Set(
      (answer.match(EXPORT_URL_RE) || []).map((u) => u.replace(/[.,;]+$/, ""))
    ),
  ];
  const modelUrl =
    urls.find((u) => /\/anatomy\.glb$/i.test(u)) ||
    urls.find((u) => u.includes(".glb") && !/original_materials/i.test(u));
  const annotationsUrl = urls.find((u) => /annotations\.json/i.test(u));
  if (!modelUrl && !annotationsUrl) return null;

  const viewerFromText = urls.find((u) => u.includes("/anatomy-viewer/"));
  const viewerUrl = viewerFromText || buildViewerUrl(apiBase, modelUrl, annotationsUrl);

  return {
    status: "ok",
    part_query: partQuery,
    part_label: partQuery,
    model_url: modelUrl,
    annotations_url: annotationsUrl,
    viewer_url: viewerUrl,
  };
}

function isVerboseLlmDump(text) {
  if (!text) return false;
  return text.length > 120 && /anatomy-exports/i.test(text);
}

export default function AnatomyMcpPanel({ apiBase, language = "en" }) {
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState("");
  const [exportData, setExportData] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [mcpToolsUsed, setMcpToolsUsed] = useState([]);
  const [catalogInfo, setCatalogInfo] = useState(null);

  const base = (apiBase || "").replace(/\/+$/, "");

  async function sendToMcp() {
    const text = message.trim();
    if (!text) {
      setStatus(t(language, "mcpEnterStructure"));
      return;
    }

    setBusy(true);
    setStatus(t(language, "mcpRunning"));
    setErrorMessage("");
    setExportData(null);
    setMcpToolsUsed([]);
    setCatalogInfo(null);

    try {
      const res = await fetch(`${base}/anatomy/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, language }),
      });
      let data = {};
      const raw = await res.text();
      try {
        data = raw ? JSON.parse(raw) : {};
      } catch {
        data = { answer: raw };
      }
      if (!res.ok) {
        const detail =
          typeof data.detail === "string"
            ? data.detail
            : Array.isArray(data.detail)
              ? data.detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
              : `HTTP ${res.status}`;
        throw new Error(
          res.status === 404
            ? `${detail} ${t(language, "mcpRestartHint")}`
            : detail
        );
      }

      let exportPayload = data.anatomy_export || null;
      if (exportPayload?.status !== "ok" && isVerboseLlmDump(data.answer)) {
        const salvaged = salvageExportFromAnswer(data.answer, text, base);
        if (salvaged) exportPayload = salvaged;
      }

      const exportOk = exportPayload?.status === "ok";
      setExportData(exportPayload);
      setMcpToolsUsed(data.mcp_tools_used || []);
      setCatalogInfo(data.catalog_info || null);
      setStatus("");

      if (exportOk) {
        setErrorMessage("");
      } else if (exportPayload?.status === "error") {
        setErrorMessage(exportPayload.error || data.error || t(language, "mcpNoExport"));
      } else if (data.error) {
        setErrorMessage(data.error);
      } else if (
        /exported/i.test(data.answer || "") &&
        !exportOk
      ) {
        setErrorMessage(t(language, "mcpExportUrlsError"));
      } else if (isVerboseLlmDump(data.answer)) {
        setErrorMessage(t(language, "mcpExportUrlsError"));
      } else if (data.answer) {
        setErrorMessage(data.answer);
      } else {
        setErrorMessage(t(language, "mcpNoExport"));
      }
    } catch (err) {
      setStatus("");
      setErrorMessage(String(err));
    } finally {
      setBusy(false);
    }
  }

  function clearPanel() {
    setMessage("");
    setStatus("");
    setErrorMessage("");
    setExportData(null);
    setMcpToolsUsed([]);
    setCatalogInfo(null);
  }

  return (
    <aside className="mcp-panel">
      <div className="mcp-panel__header">
        <Box size={20} />
        <div>
          <h2>{t(language, "mcpTitle")}</h2>
          <p className="mcp-panel__subtitle">{t(language, "mcpSubtitle")}</p>
          <p className="mcp-panel__hint">
            {t(language, "mcpCatalogSearched")}:{" "}
            <strong>
              {catalogInfo?.catalog_name || t(language, "mcpCatalogDefault")}
            </strong>
            {catalogInfo?.source_blend ? ` · ${catalogInfo.source_blend}` : ""}
          </p>
        </div>
      </div>

      <div className="mcp-panel__body">
        <label className="mcp-panel__label" htmlFor="mcp-message">
          {t(language, "mcpRequestLabel")}
        </label>
        <textarea
          id="mcp-message"
          className="mcp-panel__textarea"
          placeholder={t(language, "mcpPlaceholder")}
          value={message}
          rows={2}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendToMcp();
            }
          }}
          disabled={busy}
        />

        <div className="mcp-panel__actions">
          <button
            type="button"
            className="mcp-panel__btn mcp-panel__btn--primary"
            onClick={sendToMcp}
            disabled={busy || !message.trim()}
          >
            {busy ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
            {t(language, "send")}
          </button>
          <button
            type="button"
            className="mcp-panel__btn mcp-panel__btn--ghost"
            onClick={clearPanel}
            disabled={busy}
            title={t(language, "mcpClear")}
          >
            <RefreshCw size={16} />
          </button>
        </div>

        {status && <p className="mcp-panel__status">{status}</p>}

        {exportData?.status === "ok" && mcpToolsUsed.length > 0 && (
          <p className="mcp-panel__tools-inline">
            {t(language, "mcpTools")}: {mcpToolsUsed.join(" → ")}
          </p>
        )}

        {errorMessage && exportData?.status !== "ok" && (
          <div className="mcp-panel__answer mcp-panel__answer--error">{errorMessage}</div>
        )}

        <AnatomyExportPanel exportData={exportData} language={language} />

        {exportData?.viewer_url && exportData.status === "ok" && (
          <div className="mcp-panel__viewer-wrap">
            <iframe
              className="mcp-panel__viewer-frame"
              src={exportData.viewer_url}
              title={`${t(language, "mcpViewerTitle")}: ${exportData.part_label || "anatomy"}`}
            />
          </div>
        )}
      </div>
    </aside>
  );
}

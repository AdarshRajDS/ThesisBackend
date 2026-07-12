"use client";

import { useState, useCallback } from "react";
import { Box, Send, Loader2, RefreshCw } from "lucide-react";
import AnatomyExportPanel from "./AnatomyExportPanel";
import AnatomySuggestionList from "./AnatomySuggestionList";
import { normalizeAnatomyUrls, resolveExportPayload } from "../lib/anatomyUrls";
import { t } from "../i18n/strings";

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
  const [catalogSuggestions, setCatalogSuggestions] = useState([]);
  const [suggestionLabels, setSuggestionLabels] = useState([]);

  const base = (apiBase || "").replace(/\/+$/, "");

  const exportLabel = useCallback(
    async (label) => {
      const part = (label || "").trim();
      if (!part) return;

      setBusy(true);
      setStatus(t(language, "mcpExportingLabel", { label: part }));
      setErrorMessage("");

      try {
        const res = await fetch(`${base}/anatomy/export/direct`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ part_query: part, include_preview: true }),
        });
        const data = await res.json();
        setExportData(normalizeAnatomyUrls(data, base));
        setMcpToolsUsed(["export/direct"]);

        if (data.status === "ok") {
          setErrorMessage("");
          setStatus("");
          setMessage(part);
        } else {
          setErrorMessage(data.error || t(language, "mcpNoExport"));
          setCatalogSuggestions(data.suggestions || []);
          setSuggestionLabels(data.suggestion_labels || data.matches || []);
          setStatus("");
        }
      } catch (err) {
        setErrorMessage(String(err));
        setStatus("");
      } finally {
        setBusy(false);
      }
    },
    [base, language]
  );

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
    setCatalogSuggestions([]);
    setSuggestionLabels([]);

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

      let exportPayload = resolveExportPayload(data.anatomy_export, data.answer, text, base);

      const exportOk = exportPayload?.status === "ok";
      setExportData(exportPayload);
      setMcpToolsUsed(data.mcp_tools_used || []);
      setCatalogInfo(data.catalog_info || null);
      setCatalogSuggestions(data.catalog_suggestions || exportPayload?.suggestions || []);
      setSuggestionLabels(
        data.suggestion_labels ||
          exportPayload?.suggestion_labels ||
          exportPayload?.matches ||
          []
      );
      setStatus("");

      if (exportOk) {
        setErrorMessage("");
      } else if (exportPayload?.status === "error") {
        setErrorMessage(exportPayload.error || data.error || t(language, "mcpNoExport"));
        if (exportPayload.suggestions?.length) {
          setCatalogSuggestions(exportPayload.suggestions);
        }
        if (exportPayload.suggestion_labels?.length) {
          setSuggestionLabels(exportPayload.suggestion_labels);
        }
      } else if (data.error) {
        setErrorMessage(data.error);
      } else if (/exported/i.test(data.answer || "") && !exportOk) {
        setErrorMessage(t(language, "mcpExportUrlsError"));
      } else if (isVerboseLlmDump(data.answer)) {
        setErrorMessage(t(language, "mcpExportUrlsError"));
      } else if (data.answer) {
        setErrorMessage(data.answer);
      } else {
        setErrorMessage(t(language, "mcpNoExport"));
      }

      if (!exportOk && !(data.catalog_suggestions?.length || data.suggestion_labels?.length)) {
        const suggestRes = await fetch(
          `${base}/anatomy/suggest?q=${encodeURIComponent(text)}&limit=8&include_nearby=true`
        );
        if (suggestRes.ok) {
          const suggestData = await suggestRes.json();
          if (suggestData.suggestions?.length) {
            setCatalogSuggestions(suggestData.suggestions);
            setSuggestionLabels(suggestData.suggestion_labels || []);
          }
        }
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
    setCatalogSuggestions([]);
    setSuggestionLabels([]);
  }

  const showSuggestions =
    exportData?.status !== "ok" &&
    (catalogSuggestions.length > 0 || suggestionLabels.length > 0);

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

        {showSuggestions && (
          <AnatomySuggestionList
            language={language}
            suggestions={catalogSuggestions}
            suggestionLabels={suggestionLabels}
            onSelect={exportLabel}
            busy={busy}
          />
        )}

        <AnatomyExportPanel
          exportData={exportData}
          language={language}
          onSelectSuggestion={exportLabel}
          busy={busy}
        />

        {exportData?.viewer_url && exportData.status === "ok" && (
          <div className="mcp-panel__viewer-wrap">
            <iframe
              className="mcp-panel__viewer-frame"
              src={exportData.viewer_url}
              title={`${t(language, "mcpViewerTitle")}: ${exportData.part_label || "anatomy"}`}
            />
          </div>
        )}

        {exportData?.preview_url && exportData.status === "ok" && !exportData.viewer_url && (
          <div className="mcp-panel__preview-wrap">
            <img
              className="mcp-panel__preview-img"
              src={exportData.preview_url}
              alt={exportData.part_label || t(language, "anatomyPart")}
            />
          </div>
        )}
      </div>
    </aside>
  );
}

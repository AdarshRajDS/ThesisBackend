"use client";

import { useState, useCallback } from "react";
import { FileText, ExternalLink, Box } from "lucide-react";
import AnatomySuggestionList from "./AnatomySuggestionList";
import { normalizeAnatomyUrls, normalizeRender3dFields } from "../lib/anatomyUrls";
import { t } from "../i18n/strings";

function formatSourceLabel(language, source, page) {
  const doc = source || t(language, "uploadedDocument");
  if (page != null && page !== "") {
    return `${doc} — ${t(language, "page")} ${page}`;
  }
  return doc;
}

function primarySourceBadge(language, sources) {
  if (!sources?.length) return null;
  const s = sources[0];
  return formatSourceLabel(language, s.source, s.page);
}

export default function ChatMessage({ item, language = "en", apiBase }) {
  const isUser = item.role === "user";
  const isThinking = item.thinking;
  const [exportBusy, setExportBusy] = useState(false);
  const [inlineExport, setInlineExport] = useState(null);

  const base = (apiBase || "").replace(/\/+$/, "");

  const exportSuggestion = useCallback(
    async (label) => {
      if (!base || !label) return;
      setExportBusy(true);
      try {
        const res = await fetch(`${base}/anatomy/export/direct`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ part_query: label, include_preview: true }),
        });
        const data = await res.json();
        if (data.status === "ok") {
          setInlineExport(normalizeAnatomyUrls(data, base));
        }
      } catch {
        /* inline export is best-effort */
      } finally {
        setExportBusy(false);
      }
    },
    [base]
  );

  const showDocumentSources =
    !isUser &&
    !item.worldKnowledgeUsed &&
    !item.requiresWorldKnowledgeConsent &&
    item.localContentFound !== false &&
    !!item.sources?.length;
  const displaySources = (item.sources || []).slice(0, 3);

  const sourceLabel = primarySourceBadge(language, item.sources);
  const render3d = inlineExport
    ? {
        url: inlineExport.preview_url,
        modelUrl: inlineExport.model_url,
        anatomy: inlineExport.part_label || inlineExport.part_query,
        previewUrl: inlineExport.preview_url,
        viewerUrl: inlineExport.viewer_url,
        modelUrlDirect: inlineExport.model_url,
      }
    : normalizeRender3dFields(
        {
          render3dUrl: item.render3dUrl,
          render3dModelUrl: item.render3dModelUrl,
          render3dAnatomy: item.render3dAnatomy,
          render3dViewerUrl: item.render3dViewerUrl,
          render3dAnnotationsUrl: item.render3dAnnotationsUrl,
        },
        base
      );
  const render3dView = inlineExport
    ? render3d
    : {
        url: render3d.render3dUrl,
        modelUrl: render3d.render3dModelUrl,
        anatomy: render3d.render3dAnatomy,
        previewUrl: render3d.render3dUrl,
        viewerUrl: render3d.render3dViewerUrl,
        modelUrlDirect: render3d.render3dModelUrl,
      };

  const has3d =
    render3dView.url ||
    render3dView.previewUrl ||
    render3dView.viewerUrl ||
    render3dView.modelUrl ||
    render3dView.modelUrlDirect;

  return (
    <article className={`message message-${isUser ? "user" : "ai"}`}>
      <div className="message-avatar">
        {isUser ? (
          <div className="avatar-user">A</div>
        ) : (
          <div className="avatar-ai">
            <span className="ai-icon">🧠</span>
          </div>
        )}
      </div>

      <div className="message-content">
        {!isUser && sourceLabel && (
          <div className="source-badge">
            <FileText size={12} />
            <span>{sourceLabel}</span>
          </div>
        )}

        {!isUser && item.questionType && (
          <span className="type-badge">{item.questionType}</span>
        )}

        <div className={`message-text${isThinking ? " thinking" : ""}`}>{item.text}</div>

        {showDocumentSources && (
          <div className="msg-sources">
            <h4>{t(language, "referencesTitle")}</h4>
            <ol className="msg-sources-list">
              {displaySources.map((src, i) => (
                <li key={`${src.source}-${src.page}-${i}`} className="msg-source-item">
                  <strong>
                    [{i + 1}] {formatSourceLabel(language, src.source, src.page)}
                  </strong>
                  {src.chunk_preview && (
                    <blockquote className="msg-source-quote" title={src.chunk_preview}>
                      {src.chunk_preview}
                    </blockquote>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}

        {!!item.images?.length && (
          <div className="retrieved-images">
            {item.images.map((url) => (
              <img key={url} src={url} alt={t(language, "figureAlt")} />
            ))}
          </div>
        )}

        {!isUser && has3d && (
          <div className="message-3d-block">
            <h4 className="message-3d-block__title">
              <Box size={14} />
              {t(language, "rag3dTitle")}
              {render3dView.anatomy ? `: ${render3dView.anatomy}` : ""}
            </h4>
            {(render3dView.previewUrl || render3dView.url) && (
              <img
                className="message-3d-block__img"
                src={render3dView.previewUrl || render3dView.url}
                alt={render3dView.anatomy || t(language, "anatomyPart")}
              />
            )}
            <div className="message-3d-block__links">
              {render3dView.viewerUrl && (
                <a href={render3dView.viewerUrl} target="_blank" rel="noreferrer">
                  <ExternalLink size={12} />
                  {t(language, "viewer")}
                </a>
              )}
              {(render3dView.modelUrlDirect || render3dView.modelUrl) && (
                <a
                  href={render3dView.modelUrlDirect || render3dView.modelUrl}
                  target="_blank"
                  rel="noreferrer"
                >
                  <ExternalLink size={12} />
                  {t(language, "glb")}
                </a>
              )}
            </div>
          </div>
        )}

        {!isUser && !has3d && !!item.render3dSuggestions?.length && base && (
          <AnatomySuggestionList
            language={language}
            suggestionLabels={item.render3dSuggestions}
            onSelect={exportSuggestion}
            busy={exportBusy}
            compact
          />
        )}

        {!!item.externalSources?.length && (
          <div className="external-sources">
            <h4>{t(language, "externalRefsTitle")}</h4>
            {item.externalSources.map((url) => (
              <a key={url} href={url} target="_blank" rel="noreferrer">
                <ExternalLink size={12} />
                {url}
              </a>
            ))}
          </div>
        )}

        {item.confidence?.overall != null && (
          <div className="confidence-badge">
            {t(language, "confidence")}: {Math.round(item.confidence.overall * 100)}%
          </div>
        )}
      </div>
    </article>
  );
}

"use client";

import { FileText, ExternalLink } from "lucide-react";
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

export default function ChatMessage({ item, language = "en" }) {
  const isUser = item.role === "user";
  const isThinking = item.thinking;

  const showDocumentSources =
    !isUser &&
    !item.worldKnowledgeUsed &&
    !item.requiresWorldKnowledgeConsent &&
    item.localContentFound !== false &&
    !!item.sources?.length;
  const displaySources = (item.sources || []).slice(0, 3);

  const sourceLabel = primarySourceBadge(language, item.sources);

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

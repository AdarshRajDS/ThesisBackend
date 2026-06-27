"use client";

import { useRef, useEffect } from "react";
import { Send, Paperclip, X, Loader2 } from "lucide-react";
import { t } from "../i18n/strings";

const MIN_INPUT_HEIGHT = 52;
const MAX_INPUT_HEIGHT = 200;

export default function ChatComposer({
  language = "en",
  question,
  onQuestionChange,
  onSend,
  attachedFile,
  onAttachFile,
  onClearAttach,
  uploading,
  onKeyDown,
}) {
  const fileRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(Math.max(el.scrollHeight, MIN_INPUT_HEIGHT), MAX_INPUT_HEIGHT);
    el.style.height = `${next}px`;
    el.style.overflowY = el.scrollHeight > MAX_INPUT_HEIGHT ? "auto" : "hidden";
  }, [question]);

  return (
    <div className="input-area input-area--wide">
      {attachedFile && (
        <div className="attach-chip-row">
          <span className="attach-chip">
            <Paperclip size={14} />
            {attachedFile.name}
            <button
              type="button"
              className="attach-chip-clear"
              onClick={onClearAttach}
              aria-label={t(language, "removeAttachment")}
            >
              <X size={14} />
            </button>
          </span>
          {uploading && (
            <span className="attach-uploading">
              <Loader2 size={14} className="spin" />
              {t(language, "indexingPdf")}
            </span>
          )}
        </div>
      )}

      <div className="input-container input-container--wide">
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden-file-input"
          onChange={(e) => {
            const f = e.target.files?.[0] || null;
            onAttachFile?.(f);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          className="attach-btn"
          title={t(language, "attachPdfTitle")}
          onClick={() => fileRef.current?.click()}
        >
          <Paperclip size={18} />
        </button>
        <textarea
          ref={textareaRef}
          className="message-input message-input--grow"
          placeholder={t(language, "composerPlaceholder")}
          value={question}
          rows={1}
          onChange={(e) => onQuestionChange(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button
          type="button"
          className="send-btn"
          onClick={onSend}
          disabled={!question.trim() && !attachedFile}
          aria-label={t(language, "send")}
        >
          <Send size={20} />
        </button>
      </div>
      <div className="input-footer">
        <span className="footer-text">{t(language, "composerFooter")}</span>
      </div>
    </div>
  );
}

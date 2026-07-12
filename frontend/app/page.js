"use client";

import { useState, useEffect, useRef } from "react";
import { BookOpen, Settings, X } from "lucide-react";
import ChatMessage from "./components/ChatMessage";
import UploadPanel from "./components/UploadPanel";
import SettingsModal from "./components/SettingsModal";
import ChatComposer from "./components/ChatComposer";
import AnatomyMcpPanel from "./components/AnatomyMcpPanel";
import LanguageSelector from "./components/LanguageSelector";
import {
  loadStoredLanguage,
  storeLanguage,
  t,
  yesRegex,
} from "./i18n/strings";

export default function Page() {
  const [apiBase, setApiBase] = useState("http://127.0.0.1:8000");
  const [language, setLanguage] = useState("en");
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [resourcesOpen, setResourcesOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [healthStatus, setHealthStatus] = useState("");
  const [pdfFile, setPdfFile] = useState(null);
  const [chatAttachedFile, setChatAttachedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [pendingWorldKnowledgeQuestion, setPendingWorldKnowledgeQuestion] = useState(null);
  const messagesEndRef = useRef(null);

  const normalizedBase = (apiBase || "").trim().replace(/\/+$/, "");

  useEffect(() => {
    setLanguage(loadStoredLanguage());
  }, []);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = language === "de" ? "de" : "en";
    }
    storeLanguage(language);
  }, [language]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleLanguageChange(next) {
    setLanguage(next === "de" ? "de" : "en");
  }

  async function checkServer() {
    setHealthStatus(t(language, "checkHealth"));
    try {
      const [rootRes, anatomyRes] = await Promise.all([
        fetch(`${normalizedBase}/`),
        fetch(`${normalizedBase}/anatomy/health`),
      ]);
      const root = await rootRes.json();
      const anatomy = await anatomyRes.json();
      setHealthStatus(JSON.stringify({ backend: root, anatomy_mcp: anatomy }, null, 2));
    } catch (err) {
      setHealthStatus(`${t(language, "healthFailed")}: ${err}`);
    }
  }

  async function uploadPdfFile(file) {
    if (!file) return false;
    setUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${normalizedBase}/upload-pdf/`, { method: "POST", body: fd });
      const data = await res.json();
      setUploadedFiles((prev) => [
        { name: file.name, size: file.size },
        ...prev.filter((f) => f.name !== file.name),
      ]);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: data.message || `${t(language, "indexed")}: ${file.name}`,
        },
      ]);
      return true;
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `${t(language, "uploadFailed")}: ${err}` },
      ]);
      return false;
    } finally {
      setUploading(false);
    }
  }

  async function sendQuestion() {
    const q = question.trim();
    const hasAttach = !!chatAttachedFile;
    if (!q && !hasAttach) return;

    if (hasAttach) {
      setMessages((prev) => [
        ...prev,
        { role: "user", text: `📎 ${t(language, "attachedPdf")}: ${chatAttachedFile.name}` },
      ]);
      const ok = await uploadPdfFile(chatAttachedFile);
      if (ok) setChatAttachedFile(null);
      if (!q) return;
    }

    setQuestion("");

    const allowWorldKnowledge =
      !!pendingWorldKnowledgeQuestion && yesRegex(language).test(q);
    const questionToSend = allowWorldKnowledge ? pendingWorldKnowledgeQuestion : q;

    if (!allowWorldKnowledge) {
      setMessages((prev) => [...prev, { role: "user", text: q }]);
    }

    setMessages((prev) => [
      ...prev,
      { role: "assistant", text: t(language, "thinking"), thinking: true },
    ]);

    try {
      const res = await fetch(`${normalizedBase}/rag/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: questionToSend,
          allow_world_knowledge: allowWorldKnowledge,
          language,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setPendingWorldKnowledgeQuestion(data.pending_world_knowledge_question || null);

      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          text: data.answer || t(language, "noAnswer"),
          sources: data.sources || [],
          localContentFound: data.local_content_found !== false,
          worldKnowledgeUsed: !!data.world_knowledge_used,
          requiresWorldKnowledgeConsent: !!data.requires_world_knowledge_consent,
          externalSources: data.external_sources || [],
          images: data.images || [],
          questionType: data.question_type || null,
          confidence: data.confidence || null,
          render3dUrl: data.render_3d_url || null,
          render3dModelUrl: data.render_3d_model_url || null,
          render3dViewerUrl: data.render_3d_viewer_url || null,
          render3dAnnotationsUrl: data.render_3d_annotations_url || null,
          render3dAnatomy: data.render_3d_anatomy || null,
          render3dSuggestions: data.render_3d_suggestions || [],
        };
        return updated;
      });
    } catch (err) {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: "assistant",
          text: `${t(language, "requestFailed")}: ${err}`,
        };
        return updated;
      });
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  }

  return (
    <div className="app-container app-container--split">
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <div className="logo">
              <img src="/hfu-logo.svg" alt="HFU" className="logo-img" />
              <div className="logo-text">
                <h1>{t(language, "appTitle")}</h1>
                <span className="tagline">{t(language, "tagline")}</span>
              </div>
            </div>
          </div>
          <div className="header-right">
            <LanguageSelector
              language={language}
              onChange={handleLanguageChange}
              ariaLabel={t(language, "languageAria")}
            />
            <button
              type="button"
              className="header-btn"
              onClick={() => setResourcesOpen(true)}
            >
              <BookOpen size={18} />
              <span>{t(language, "resources")}</span>
            </button>
            <button
              type="button"
              className="header-btn"
              onClick={() => setSettingsOpen(true)}
              aria-label={t(language, "settings")}
            >
              <Settings size={18} />
            </button>
          </div>
        </div>
      </header>

      <main className="main-split">
        <section className="chat-pane" aria-label={t(language, "ragPaneAria")}>
          <div className="chat-pane__label">{t(language, "ragPaneLabel")}</div>
          <div className="chat-container chat-container--pane">
            <div className="messages-area">
              {messages.length === 0 && (
                <div className="welcome-message">
                  <div className="welcome-icon">📚</div>
                  <h2>{t(language, "welcomeTitle")}</h2>
                  <p>{t(language, "welcomeBody")}</p>
                  <p className="welcome-message__hint">
                    {t(language, "welcomeHintPrefix")}
                    <strong>{t(language, "welcomeHintBold")}</strong>
                    {t(language, "welcomeHintSuffix")}
                  </p>
                </div>
              )}

              {messages.map((item, idx) => (
                <ChatMessage
                  key={`msg-${idx}`}
                  item={item}
                  language={language}
                  apiBase={normalizedBase}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>

            <ChatComposer
              language={language}
              question={question}
              onQuestionChange={setQuestion}
              onSend={sendQuestion}
              attachedFile={chatAttachedFile}
              onAttachFile={setChatAttachedFile}
              onClearAttach={() => setChatAttachedFile(null)}
              uploading={uploading}
              onKeyDown={handleKeyDown}
            />
          </div>
        </section>

        <AnatomyMcpPanel apiBase={normalizedBase} language={language} />
      </main>

      {resourcesOpen && (
        <div className="modal-overlay" onClick={() => setResourcesOpen(false)}>
          <div
            className="modal-card resources-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label={t(language, "knowledgeBaseAria")}
          >
            <div className="modal-header">
              <h2>{t(language, "knowledgeBase")}</h2>
              <button
                type="button"
                className="modal-close"
                onClick={() => setResourcesOpen(false)}
                aria-label={t(language, "close")}
              >
                <X size={18} />
              </button>
            </div>
            <UploadPanel
              language={language}
              isOpen
              onToggle={() => setResourcesOpen(false)}
              pdfFile={pdfFile}
              onFileChange={setPdfFile}
              onUpload={() => uploadPdfFile(pdfFile)}
              uploading={uploading}
              uploadedFiles={uploadedFiles}
            />
          </div>
        </div>
      )}

      <SettingsModal
        language={language}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        apiBase={apiBase}
        onApiBaseChange={setApiBase}
        onCheckHealth={checkServer}
        healthStatus={healthStatus}
      />
    </div>
  );
}

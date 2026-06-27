"use client";

import {
  Upload,
  BookOpen,
  ChevronDown,
  FileText,
  AlertCircle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { t } from "../i18n/strings";

function formatBytes(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadPanel({
  language = "en",
  isOpen,
  onToggle,
  pdfFile,
  onFileChange,
  onUpload,
  uploading,
  uploadedFiles = [],
}) {
  return (
    <div className={`upload-panel ${isOpen ? "open" : ""}`}>
      <button type="button" className="panel-toggle" onClick={onToggle}>
        <Upload size={18} />
        <span>{t(language, "uploadPanelTitle")}</span>
        <ChevronDown size={16} className={isOpen ? "rotated" : ""} />
      </button>

      {isOpen && (
        <div className="panel-content">
          <div className="upload-section">
            <div className="section-header">
              <BookOpen size={16} />
              <span>{t(language, "pdfResources")}</span>
            </div>
            <div className="upload-area">
              <input
                type="file"
                id="pdf-upload"
                accept=".pdf"
                hidden
                onChange={(e) => onFileChange(e.target.files?.[0] || null)}
              />
              <label htmlFor="pdf-upload" className="upload-label">
                <Upload size={24} />
                <span>{pdfFile ? pdfFile.name : t(language, "uploadPdfLabel")}</span>
                <small>{t(language, "uploadPdfHint")}</small>
              </label>
              {pdfFile && (
                <button
                  type="button"
                  className="upload-submit-btn"
                  onClick={onUpload}
                  disabled={uploading}
                >
                  {uploading ? (
                    <>
                      <Loader2 size={16} className="spin" />
                      {t(language, "processing")}
                    </>
                  ) : (
                    t(language, "indexDocument")
                  )}
                </button>
              )}
            </div>

            {uploadedFiles.length > 0 && (
              <div className="uploaded-files">
                {uploadedFiles.map((f) => (
                  <div key={f.name} className="file-item">
                    <FileText size={16} />
                    <div className="file-info">
                      <span className="file-name">{f.name}</span>
                      <span className="file-size">{formatBytes(f.size)}</span>
                    </div>
                    <CheckCircle2 size={16} className="file-status" />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="consent-section">
            <div className="consent-info">
              <AlertCircle size={16} />
              <div>
                <strong>{t(language, "privacyTitle")}</strong>
                <p>{t(language, "privacyBody")}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

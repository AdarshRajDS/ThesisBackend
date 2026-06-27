"use client";

import { X } from "lucide-react";
import { t } from "../i18n/strings";

export default function SettingsModal({
  language = "en",
  open,
  onClose,
  apiBase,
  onApiBaseChange,
  onCheckHealth,
  healthStatus,
}) {
  if (!open) return null;

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true">
      <div className="modal-card">
        <div className="modal-header">
          <h2>{t(language, "settings")}</h2>
          <button
            type="button"
            className="modal-close"
            onClick={onClose}
            aria-label={t(language, "close")}
          >
            <X size={20} />
          </button>
        </div>
        <label className="settings-field">
          {t(language, "backendApiUrl")}
          <input
            type="url"
            value={apiBase}
            onChange={(e) => onApiBaseChange(e.target.value)}
            placeholder="http://127.0.0.1:8000"
          />
        </label>
        <button type="button" className="settings-check-btn" onClick={onCheckHealth}>
          {t(language, "checkConnection")}
        </button>
        {healthStatus && <pre className="settings-health">{healthStatus}</pre>}
      </div>
    </div>
  );
}

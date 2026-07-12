"use client";

import { Loader2 } from "lucide-react";
import { t } from "../i18n/strings";

function formatReason(language, reason) {
  const key = `suggestReason_${reason}`;
  const localized = t(language, key);
  return localized !== key ? localized : reason;
}

export default function AnatomySuggestionList({
  language = "en",
  suggestions = [],
  suggestionLabels = [],
  onSelect,
  busy = false,
  compact = false,
}) {
  const rows =
    suggestions?.length > 0
      ? suggestions
      : (suggestionLabels || []).map((label) => ({ label, can_export: true }));

  if (!rows.length) return null;

  return (
    <div className={`anatomy-suggestions${compact ? " anatomy-suggestions--compact" : ""}`}>
      <p className="anatomy-suggestions__title">{t(language, "exportableSuggestions")}</p>
      <ul className="anatomy-suggestions__list">
        {rows.map((row) => {
          const label = typeof row === "string" ? row : row.label;
          if (!label) return null;
          const reason =
            typeof row === "object" && row.match_reason
              ? formatReason(language, row.match_reason)
              : null;
          const confidence =
            typeof row === "object" && row.confidence != null
              ? Math.round(Number(row.confidence) * 100)
              : null;
          return (
            <li key={label}>
              <button
                type="button"
                className="anatomy-suggestions__chip"
                disabled={busy || !onSelect}
                onClick={() => onSelect?.(label)}
                title={t(language, "exportSuggestionTitle")}
              >
                {busy ? <Loader2 size={14} className="spin" /> : null}
                <span className="anatomy-suggestions__label">{label}</span>
                {(reason || confidence != null) && (
                  <span className="anatomy-suggestions__meta">
                    {reason}
                    {reason && confidence != null ? " · " : ""}
                    {confidence != null ? `${confidence}%` : ""}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

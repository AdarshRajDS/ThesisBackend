"use client";

import { Languages } from "lucide-react";
import { LANGUAGES } from "../i18n/strings";

export default function LanguageSelector({ language, onChange, ariaLabel }) {
  return (
    <label className="lang-selector">
      <Languages size={16} aria-hidden />
      <select
        className="lang-selector__select"
        value={language}
        onChange={(e) => onChange(e.target.value)}
        aria-label={ariaLabel}
      >
        {LANGUAGES.map(({ code, label }) => (
          <option key={code} value={code}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}

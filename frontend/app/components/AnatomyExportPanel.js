"use client";

import { Box, Download, ExternalLink, FileJson } from "lucide-react";
import { t } from "../i18n/strings";

export default function AnatomyExportPanel({ exportData, language = "en" }) {
  if (!exportData) return null;

  const isOk = exportData.status === "ok";

  if (!isOk) {
    const message = exportData.error || t(language, "exportUnavailable");
    return (
      <div className="anatomy-export anatomy-export--error">
        <p className="anatomy-export__title">{t(language, "exportTitle")}</p>
        <p className="anatomy-export__error">{message}</p>
        {!!exportData.matches?.length && (
          <p className="anatomy-export__hint">
            {t(language, "didYouMean")}: {exportData.matches.join(", ")}?
          </p>
        )}
        {exportData.instruction && (
          <p className="anatomy-export__hint">{exportData.instruction}</p>
        )}
      </div>
    );
  }

  const title = exportData.part_label || exportData.part_query || t(language, "anatomyPart");
  const annotationCount = exportData.annotation_count ?? 0;

  return (
    <div className="anatomy-export">
      <div className="anatomy-export__header">
        <Box size={16} />
        <span>{title}</span>
        {annotationCount > 0 && (
          <span className="anatomy-export__badge">
            {annotationCount} {t(language, "labels")}
          </span>
        )}
      </div>

      <div className="anatomy-export__deliverables">
        {exportData.viewer_url ? (
          <a
            className="anatomy-export__btn anatomy-export__btn--primary"
            href={exportData.viewer_url}
            target="_blank"
            rel="noreferrer"
            title={t(language, "openViewer")}
          >
            <ExternalLink size={14} />
            {t(language, "viewer")}
          </a>
        ) : (
          <span className="anatomy-export__missing">{t(language, "noViewer")}</span>
        )}
        {exportData.model_url ? (
          <a
            className="anatomy-export__btn"
            href={exportData.model_url}
            download
            target="_blank"
            rel="noreferrer"
            title={t(language, "downloadGlb")}
          >
            <Download size={14} />
            {t(language, "glb")}
          </a>
        ) : (
          <span className="anatomy-export__missing">{t(language, "noGlb")}</span>
        )}
        {exportData.annotations_url ? (
          <a
            className="anatomy-export__btn"
            href={exportData.annotations_url}
            download
            target="_blank"
            rel="noreferrer"
            title={t(language, "downloadAnnotations")}
          >
            <FileJson size={14} />
            {t(language, "annotations")}
          </a>
        ) : (
          <span className="anatomy-export__missing">{t(language, "noAnnotations")}</span>
        )}
      </div>
    </div>
  );
}

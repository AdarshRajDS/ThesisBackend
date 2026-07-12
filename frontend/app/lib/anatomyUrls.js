const EXPORT_URL_RE = /https?:\/\/[^\s)\]"']+/gi;
const MARKDOWN_LINK_RE = /\]\((https?:\/\/[^)]+)\)/gi;

export function extractUrlsFromText(text) {
  if (!text) return [];
  const urls = new Set();
  for (const match of text.matchAll(MARKDOWN_LINK_RE)) {
    urls.add(match[1].replace(/[.,;]+$/, ""));
  }
  for (const match of text.match(EXPORT_URL_RE) || []) {
    urls.add(match.replace(/[.,;]+$/, ""));
  }
  return [...urls];
}

export function parseViewerParams(viewerUrl) {
  try {
    const parsed = new URL(viewerUrl);
    if (!parsed.pathname.includes("/anatomy-viewer/")) return null;
    const modelUrl = parsed.searchParams.get("model");
    const annotationsUrl = parsed.searchParams.get("annotations");
    if (!modelUrl) return null;
    return { modelUrl, annotationsUrl };
  } catch {
    return null;
  }
}

export function buildViewerUrl(apiBase, modelUrl, annotationsUrl) {
  if (!modelUrl || !annotationsUrl) return null;
  const origin = (apiBase || "http://127.0.0.1:8000").replace(/\/+$/, "");
  return `${origin}/anatomy-viewer/index.html?model=${encodeURIComponent(modelUrl)}&annotations=${encodeURIComponent(annotationsUrl)}`;
}

export function fixAnatomyUrl(url, origin) {
  if (!url || typeof url !== "string") return url;
  try {
    const parsed = new URL(url);
    const base = new URL(origin);
    if (
      parsed.pathname.includes("/anatomy-exports/") ||
      parsed.pathname.includes("/anatomy-viewer/")
    ) {
      return `${base.origin}${parsed.pathname}${parsed.search}`;
    }
  } catch {
    return url;
  }
  return url;
}

/** Always rebuild viewer_url from model + annotations on the API origin. */
export function normalizeAnatomyUrls(exportData, apiBase) {
  if (!exportData || exportData.status !== "ok") return exportData;
  const origin = (apiBase || "http://127.0.0.1:8000").replace(/\/+$/, "");

  const modelUrl = fixAnatomyUrl(exportData.model_url, origin);
  const annotationsUrl = fixAnatomyUrl(exportData.annotations_url, origin);
  const previewUrl = fixAnatomyUrl(exportData.preview_url, origin);
  const viewerUrl = buildViewerUrl(origin, modelUrl, annotationsUrl);

  return {
    ...exportData,
    model_url: modelUrl,
    annotations_url: annotationsUrl,
    preview_url: previewUrl,
    viewer_url: viewerUrl,
  };
}

export function normalizeRender3dFields(item, apiBase) {
  if (!item) return item;
  const origin = (apiBase || "http://127.0.0.1:8000").replace(/\/+$/, "");
  const modelUrl = fixAnatomyUrl(item.render3dModelUrl, origin);
  const annotationsUrl = fixAnatomyUrl(item.render3dAnnotationsUrl, origin);
  const viewerUrl =
    buildViewerUrl(origin, modelUrl, annotationsUrl) ||
    fixAnatomyUrl(item.render3dViewerUrl, origin);

  return {
    ...item,
    render3dUrl: fixAnatomyUrl(item.render3dUrl, origin),
    render3dModelUrl: modelUrl,
    render3dAnnotationsUrl: annotationsUrl,
    render3dViewerUrl: viewerUrl,
  };
}

export function salvageExportFromAnswer(answer, partQuery, apiBase) {
  if (!answer || !/(anatomy-exports|anatomy-viewer)/i.test(answer)) return null;

  const urls = extractUrlsFromText(answer);
  const viewerFromText = urls.find((u) => u.includes("/anatomy-viewer/"));
  const fromViewer = viewerFromText ? parseViewerParams(viewerFromText) : null;

  let modelUrl = fromViewer?.modelUrl || null;
  let annotationsUrl = fromViewer?.annotationsUrl || null;

  if (!modelUrl) {
    modelUrl =
      urls.find((u) => /\/anatomy\.glb$/i.test(u)) ||
      urls.find(
        (u) =>
          u.includes(".glb") &&
          !/original_materials/i.test(u) &&
          !u.includes("/anatomy-viewer/")
      );
  }
  if (!annotationsUrl) {
    annotationsUrl = urls.find(
      (u) => /annotations\.json/i.test(u) && !u.includes("/anatomy-viewer/")
    );
  }
  if (!modelUrl && !annotationsUrl) return null;

  return normalizeAnatomyUrls(
    {
      status: "ok",
      part_query: partQuery,
      part_label: partQuery,
      model_url: modelUrl,
      annotations_url: annotationsUrl,
    },
    apiBase
  );
}

export function answerNeedsSalvage(answer, exportPayload) {
  if (exportPayload?.status === "ok") return false;
  if (!answer) return false;
  return /(anatomy-exports|anatomy-viewer)/i.test(answer);
}

export function resolveExportPayload(exportPayload, answer, partQuery, apiBase) {
  let payload = exportPayload || null;
  if (answerNeedsSalvage(answer, payload)) {
    const salvaged = salvageExportFromAnswer(answer, partQuery, apiBase);
    if (salvaged) payload = salvaged;
  }
  return payload ? normalizeAnatomyUrls(payload, apiBase) : null;
}

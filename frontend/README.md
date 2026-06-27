# HFU Anatomy Chatbot — Frontend

Next.js 16 app for the multimodal anatomy RAG backend.

## Features

- **Chat** — grounded answers from uploaded PDFs (`POST /rag/ask`)
- **PDF attach** — paperclip in the composer indexes via `POST /upload-pdf/`
- **Anatomy MCP 3D** — when a body part is detected, RAG attaches `anatomy_export` with annotated viewer + GLB download
- **Resources** — header modal for bulk PDF upload
- **Settings** — API base URL and health check
- **Theme** — WhatsApp-green accents, full-width chat (no sidebar)

## Quick start

```powershell
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:3000** (backend default: **http://127.0.0.1:8000**).

Start the full stack from repo root:

```powershell
..\scripts\start_full_stack.ps1
```

## Project layout

| Path | Description |
|------|-------------|
| `app/page.js` | Main page: messages, composer, modals |
| `app/layout.js` | Root layout |
| `app/globals.css` | Imports `anatomy-chatbot.css`, theme, extensions |
| `app/components/ChatComposer.js` | Auto-growing textarea + PDF attach |
| `app/components/ChatMessage.js` | AI/user bubbles, sources, anatomy export panel |
| `app/components/AnatomyExportPanel.js` | 3D preview, viewer link, GLB download |
| `app/components/UploadPanel.js` | Knowledge-base PDF upload |
| `app/components/SettingsModal.js` | API base URL and health check |

## API integration

```javascript
// Ask question
POST {apiBase}/rag/ask
{ "question": "...", "allow_world_knowledge": false }

// Attach PDF (FormData)
POST {apiBase}/upload-pdf/

// Anatomy MCP (optional)
GET {apiBase}/anatomy/health
GET {apiBase}/anatomy/search?q=liver
POST {apiBase}/anatomy/export
```

RAG responses may include `anatomy_export.viewer_url` — opens the Three.js annotation viewer served at `/anatomy-viewer/`.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server on port 3000 |
| `npm run build` | Production build |
| `npm run start` | Serve production build |

## Requirements

- Node.js 18+
- Backend running on port 8000 (see repo `RUNBOOK.md`)
- LM Studio (or configured LLM) for chat answers

## Full documentation

See **[../RUNBOOK.md](../RUNBOOK.md)** for backend, MinIO, evaluation, and troubleshooting.

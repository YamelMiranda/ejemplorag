# CORA RAG

Backend RAG de CORA (FastAPI) que conecta el panel `cora-admin.html` con el
pipeline armado en `notebook/document.ipynb` y `notebook/pdfloader.ipynb`.

## 1. Instalación

```bash
python -m venv .venv
source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configuración

```bash
cp .env.example .env
```

Edita `.env` y coloca tu `GROQ_API_KEY` (https://console.groq.com).

## 3. Levantar la API

```bash
uvicorn main:app --reload --port 8000
```

La primera vez que se use el chat o se suba un documento, se descargará
automáticamente el modelo de embeddings `all-MiniLM-L6-v2` desde HuggingFace.

## 4. Abrir el panel admin

Abre `cora-admin.html` en el navegador (o sírvelo con cualquier servidor
estático). El archivo ya apunta a `http://localhost:8000/api` mediante la
constante `API_BASE` definida al inicio de su `<script>`.

## Qué está conectado

- **Chat principal ("Pregunta a CORA")** → `POST /api/chat/query`. Usa el
  mismo pipeline de `document.ipynb`/`pdfloader.ipynb` (carga → chunking →
  embeddings → ChromaDB → retrieval → generación con Groq).
- **Referencias de documentos** → cada respuesta del chat muestra los
  documentos recuperados semánticamente (fuente + % de similitud).
- **Historial de chats** (sidebar y "Tu cuenta") → `GET /api/chats`.
- **Dashboard → Total de Documentos Subidos** → `GET /api/dashboard/stats`
  (cuenta los archivos reales dentro de `data/pdf` y `data/text_files`).
- **Gestión de Documentos → subir (click o arrastrar)** →
  `POST /api/documents/upload`: guarda el archivo en `data/` y lo indexa.
- **Registros → pestaña "Documentos"** → `GET /api/documents`: lista los
  documentos actualmente guardados en `data/`.

## Estructura

El backend está organizado en capas (Clean Architecture / Ports & Adapters).
Ver `SECURITY_ROADMAP.md` para el detalle de qué pilares de seguridad cubre
cada capa y qué queda pendiente (RBAC, JWT, 2FA, Prompt Guard, etc.).

```
backend/
  core/                 config tipada, excepciones, logging, seguridad
                         (identity/authorization/audit — hoy permisivos,
                         puerto único para conectar AD/RBAC/JWT/2FA a futuro)
  domain/                entidades: DocumentMetadata (estándar de 16 campos
                         del Repositorio de Conocimiento), Chat, Message
  application/
    ports/                interfaces que consume la capa de aplicación
    use_cases/             ingest_document, answer_query, ask_cora,
                           manage_documents, manage_chats
  infrastructure/         adapters concretos: SentenceTransformer, ChromaDB,
                          Groq, loaders (PyMuPDF/Text), filesystem, sqlite
  api/                    FastAPI: routers, schemas, dependencies (DI),
                           main.py (app factory + manejo de errores + CORS)
main.py                   shim: `from backend.api.main import app`
data/                      misma carpeta que usan los notebooks
notebook/                   document.ipynb y pdfloader.ipynb originales
SECURITY_ROADMAP.md          estado de los 4 pilares de seguridad de CORA
```

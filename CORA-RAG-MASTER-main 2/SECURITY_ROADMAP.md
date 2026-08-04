# CORA — Security Roadmap

Este documento se actualiza cada vez que el backend cambia de forma
relevante para alguno de los cuatro pilares definidos en
`Arquitectura de Seguridad y Gobernanza de CORA` (data/pdf). Registra qué se
fortaleció y qué sigue pendiente — no reemplaza al documento de gobernanza,
lo operacionaliza.

## Estado actual (RBAC real de documentos, auditoría expuesta y reinicio
## forzado de contraseña, 2026-07-20)

Ronda enfocada en hacer *cumplir* de verdad lo que hasta ahora solo se
persistía (Pilar II/IV) y en exponer lo que hasta ahora solo se escribía
(Pilar III), más una serie de correcciones de UI en `static/cora-admin.html`.

- **RBAC real de documentos** (Pilar II + IV): `access_level`/
  `classification` como campos elegidos a mano se reemplazan por
  `visible_department` (departamento con visibilidad exclusiva, o `None` =
  toda la empresa) y `minimum_role` (jerárquico: `EMPLOYEE < SUPERVISOR <
  ADMIN`); `classification` pasa a derivarse automáticamente de
  `minimum_role` (`backend/domain/document.py: classification_for`). La
  regla vive en `backend/core/security/authorization.py:
  can_view_document(...)` y se aplica en dos puntos: qué documentos lista
  "Gestión de Documentos" (`ManageDocumentsUseCase.list_documents`) y qué
  chunks puede citar CORA en el chat (`AnswerQueryUseCase`). Decisión de
  diseño explícita (confirmada con el usuario): **ADMIN ve todo, sin
  excepción**, sin importar el departamento del documento. Los documentos
  ya indexados se editan sin volver a subir el archivo
  (`VectorStorePort.update_document_metadata`, `PATCH
  /api/documents/{filename}`).
- **Auditoría consultable** (Pilar III): `AuditLogger.list_events(since=)`
  ya tenía todos los eventos desde la ronda anterior pero nunca se exponían;
  ahora `GET /api/audit?period=daily|weekly|monthly` (solo ADMIN, igual
  criterio que "Gestión de Usuarios": agrega actividad de todos los
  usuarios) alimenta la vista "Registros" (una sola tabla real, ya no datos
  de ejemplo) y el gráfico de actividad semanal + "Consultas Realizadas" del
  Dashboard.
- **Reinicio forzado de contraseña** (Pilar II): `User.must_change_password`
  (default `True` al crear un usuario desde el panel) + `POST
  /api/auth/change-password` (valida la contraseña actual, reemite la
  cookie de sesión con el JWT actualizado). *Alcance acotado, decisión
  explícita*: la aplicación de la bandera es del lado del frontend (pantalla
  bloqueante) más el endpoint real de cambio; el resto de endpoints no
  verifican individualmente la bandera mientras esté activa, para no
  complejizar cada router.
- **UI**: eliminados los diálogos nativos `confirm()` en los flujos de
  borrado/desactivación (chats, documentos, usuarios) — podían dejar el
  input del chat sin foco tras cerrarse, un bug real reportado por el
  usuario. Se reemplazaron por un modal propio (`confirmModal`/
  `openFormModal` en `static/cora-admin.html`), que también se reutiliza
  para los formularios de edición de documento y usuario.

## Estado actual (rediseño a Clean Architecture, 2026-07-14)

El backend se reescribió completo, pasando de ~10 módulos planos sin capas a
una arquitectura por capas (`core/`, `domain/`, `application/`,
`infrastructure/`, `api/`) con puertos y adapters. Resumen por pilar:

### Pilar I — Protección de la Información

**Fortalecido:**
- Se eliminó la fuga de credencial activa: `backend/GROQ_API_KEY.py` (key en
  texto plano) fue borrado y `.env` salió del tracking de git
  (`.gitignore` nuevo). Todos los secretos se leen solo por variable de
  entorno (`backend/core/config.py`, `pydantic-settings`).
- Estándar de metadatos de 16 campos aplicado a **todo** chunk almacenado en
  ChromaDB (`backend/domain/document.py: DocumentMetadata`), incluyendo
  `document_hash` (sha256) para verificar integridad del contenido.
- Se corrigió una vulnerabilidad de path traversal (OWASP A01): el nombre de
  archivo recibido en upload/delete ahora se sanitiza con `Path(...).name`
  antes de tocar el filesystem (`backend/infrastructure/storage/filesystem_document_storage.py`).
- CORS dejó de ser `allow_origins=["*"]`; ahora es una lista explícita
  configurable (`CORS_ALLOW_ORIGINS`).

**Pendiente:**
- Cifrado en reposo de `data/` (documentos, ChromaDB, sqlite) y en tránsito
  más allá de HTTPS a nivel de infraestructura (no lo resuelve el código de
  aplicación).

### Pilar II — Gestión de Identidades y Accesos

**Fortalecido (login real + directorio de usuarios, 2026-07-14):**
- Autenticación real: login por correo/contraseña contra un directorio de
  usuarios propio (`backend/infrastructure/persistence/sqlite/user_repository.py`,
  `SqliteUserDirectory`), diseñado detrás de
  `backend/application/ports/user_directory_port.py` — hoy simula un
  Active Directory; conectar un LDAP/AD real más adelante es agregar un
  adapter nuevo que implemente el mismo puerto, no rediseñar el sistema.
  No hay AD/LDAP real disponible en este entorno (confirmado con el
  usuario), por eso se optó por esta simulación en vez de dejarlo sin
  implementar.
- Contraseñas con hash bcrypt (`backend/core/security/passwords.py`), nunca
  en texto plano ni siquiera en memoria más de lo necesario.
- Sesión con JWT (PyJWT, HS256) firmado con `JWT_SECRET_KEY`
  (`backend/infrastructure/security/jwt_token_service.py`), entregado en una
  **cookie httpOnly** (`cora_session`, `SameSite=Lax`) — nunca en
  localStorage ni en el cuerpo de la respuesta, para mitigar robo de sesión
  vía XSS. El frontend nunca toca el token directamente.
- `get_current_principal()` dejó de devolver un principal fijo: ahora vive
  en `backend/api/dependencies.py`, lee la cookie, valida el JWT y devuelve
  el `Principal` real — **todos** los endpoints (chat, documentos,
  dashboard, usuarios) ya exigen sesión válida (401 sin ella).
- Gestión de usuarios real: `GET/POST/PATCH/DELETE /api/users`
  (`backend/api/routers/users.py`), con rol ADMIN obligatorio verificado en
  el caso de uso (`ManageUsersUseCase`, no solo en el router) — es la
  primera superficie con control de acceso real por rol, antes de que
  exista RBAC general. Un admin no puede eliminar su propia cuenta.
- Bootstrap seguro: el primer admin se crea al arrancar desde
  `BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD` (obligatorios, sin
  default) — el arranque falla en vez de crear una cuenta adivinable.
- Panel admin conectado de verdad: login, `GET /api/auth/me` al cargar la
  página (sesión persiste entre recargas), logout, y la vista "Gestión de
  Usuarios" ya no es un arreglo local — es CRUD real contra el backend.

**Pendiente (no implementado, solo preparado):**
- Integración con un Active Directory/LDAP real (el puerto ya existe,
  falta el adapter).
- 2FA.
- Rotación/revocación de JWT antes de su expiración (hoy expiran solos a
  las `JWT_EXPIRE_MINUTES`, pero no hay lista de revocación si se necesita
  invalidar una sesión antes de tiempo).

### Pilar III — Gobernanza y Trazabilidad

**Fortalecido:**
- Auditoría real desde ya: `backend/core/security/audit.py` (puerto) +
  `backend/infrastructure/persistence/sqlite/audit_repository.py` (adapter)
  registran cada subida, consulta y eliminación (`audit_log`, en
  `data/cora_audit.db`, separado del resto del estado operativo).
- Registro de documentos con `document_id` estable y `document_version`
  incremental (`backend/application/ports/document_registry_port.py`) —
  base para versionado documental; hoy la versión más nueva reemplaza el
  contenido recuperable de la anterior, pero la identidad y el historial de
  versiones ya se conservan en `documents_registry`.
- Cada respuesta de chat sigue siendo rastreable hasta los `chunk_id`
  específicos que la respaldan (`DocumentReference` en el historial).

**Pendiente:**
- Conservar el contenido íntegro de versiones anteriores (hoy solo se
  conserva su metadata en el registro, no los chunks/embeddings viejos).
- Política de retención y protección contra manipulación del log de
  auditoría (hoy es una tabla sqlite mutable como cualquier otra).

### Pilar IV — Inteligencia Artificial Confiable

**Fortalecido:**
- El fallback "no dispone de información verificable" se mantiene como
  comportamiento por defecto cuando no hay evidencia (o evidencia
  autorizada) suficiente (`backend/application/use_cases/answer_query.py`).
- El filtrado por autorización contextual entre retrieval y generación ya
  es real: `AnswerQueryUseCase` descarta con `can_view_document(...)` todo
  chunk recuperado que el `Principal` actual no puede ver antes de
  construir el prompt (ver Pilar II) — CORA nunca cita en el chat un
  documento que el usuario no podría ver en "Gestión de Documentos".

**Pendiente (marcado explícitamente con TODO en el código):**
- Prompt Guard (sanitización de la pregunta y del contexto recuperado antes
  de construir el prompt, mitigación de prompt injection desde documentos
  indexados).
- Validación de respuesta (RA-RAG / detección de alucinaciones) antes de
  devolver la respuesta al usuario.

## Acción pendiente del usuario (no resuelta por este rediseño)

La API key de Groq que estaba committeada (`gsk_i3KiL...VsB`) ya quedó
expuesta en el historial de git. Sacarla del tracking actual no la invalida:
**debe rotarse/regenerarse en console.groq.com**.

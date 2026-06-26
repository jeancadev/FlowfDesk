# FlowDesk

> Sistema de gestión de tickets y soporte interno con búsqueda inteligente, eventos en tiempo real y arquitectura hexagonal.

FlowDesk es una plataforma backend-first diseñada para equipos de soporte que necesitan gestionar tickets, escalar incidencias y mantener trazabilidad sobre cada interacción con sus usuarios. La API expone operaciones CRUD completas sobre tickets, usuarios, comentarios y attachments, con búsqueda full-text tolerante a errores tipográficos, publicación de eventos asincrónicos (Kafka) y una interfaz web de operador integrada para monitoreo y gestión en tiempo real.

## ¿Qué resuelve?

Los sistemas de soporte internos suelen empezar como hojas de cálculo o canales de Slack que escalan mal. FlowDesk nace como una solución real que:

- **Centraliza** la creación, asignación y cierre de tickets con estados claros (`open` → `in_progress` → `waiting_on_customer` → `resolved` → `closed`).
- **Prioriza** el trabajo con niveles de urgencia (`low`, `medium`, `high`, `critical`) para que los equipos puedan hacer triage efectivo.
- **Busca de verdad** — Elasticsearch con campos boosted y fuzzy matching permite encontrar tickets aunque el operador escriba "logn" en lugar de "login".
- **Notifica y audita** automáticamente via Kafka consumers que procesan eventos de tickets sin bloquear el flujo principal.
- **Escala** horizontalmente — cada pieza (API, consumers, search, cache) corre en su propio container.

## Características Principales

| Área | Funcionalidad |
|---|---|
| **Tickets** | CRUD completo, cierre con timestamp, asignación, tags, prioridades y filtros por status/assignee |
| **Usuarios** | Creación de agentes, admins y customers con roles diferenciados |
| **Comentarios** | Hilo de conversación por ticket con autor y timestamp |
| **Attachments** | Subida de archivos a S3/MinIO con presigned URLs para descarga segura |
| **Búsqueda** | Full-text search con Elasticsearch (boost ×3 en título, ×2 en descripción, fuzziness AUTO) |
| **Eventos** | Publicación asincrónica a Kafka en topics `ticket.created`, `ticket.updated`, `ticket.closed` |
| **Rate Limiting** | Límite por IP con Redis `INCR` + TTL, graceful degradation si Redis cae |
| **Health Check** | Endpoint `/health` con estado de Redis para liveness/readiness probes |
| **Operator UI** | Interfaz web integrada con métricas, gestión de tickets/usuarios y panel de detalle |
| **Demo Mode** | Servidor standalone con mocks in-memory — sin Docker, sin PostgreSQL, sin nada externo |

## Stack Tecnológico

| Layer | Technology |
|-------|-----------|
| **API** | Python 3.11, Flask 3, Flask-RESTX (Swagger auto-generado) |
| **ORM & Migrations** | SQLAlchemy 2, Alembic |
| **Database** | PostgreSQL 16 |
| **Search** | Elasticsearch 8 (full-text, fuzzy, boosted fields) |
| **Messaging** | Apache Kafka (KRaft mode, sin Zookeeper) |
| **Cache & Rate Limiting** | Redis 7 |
| **File Storage** | AWS S3 / MinIO (compatible) |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions (lint + tests en cada push/PR) |
| **Testing** | pytest + pytest-cov, factory-boy, faker |
| **Code Quality** | Ruff (linting), mypy (type checking) |

## Arquitectura

FlowDesk sigue una **Arquitectura Hexagonal (Ports & Adapters)** donde el dominio es puro Python sin dependencias externas. La capa de infraestructura implementa los contratos (ports) definidos por el dominio, lo que permite cambiar cualquier servicio externo (base de datos, search engine, message broker) sin tocar la lógica de negocio.

```
Cliente HTTP / Operator UI
         │
         ▼
  Flask API (Flask-RESTX) ──► Swagger UI (/swagger/)
         │
         ├──► Use Cases (dominio puro — sin Flask, sin SQLAlchemy)
         │         │
         │         ├──► PostgreSQL (SQLAlchemy) — persistencia principal
         │         ├──► Elasticsearch — búsqueda full-text
         │         └──► Redis — caché y rate limiting
         │
         └──► Kafka Producer → Topics: ticket.created / ticket.updated / ticket.closed
                                    │
                                    ▼
                            Kafka Consumers
                            ├── NotificationConsumer → (log / email simulado)
                            └── AuditConsumer → guarda historial de cambios
```

### Estructura del Proyecto

```
app/
├── domain/                    ← Puro Python. CERO dependencias externas
│   ├── entities/              ← Dataclasses: Ticket, User, Comment, Attachment
│   │   └── ticket.py          ← Entidades con factory methods y transiciones de estado
│   ├── ports/                 ← Protocolos/ABCs (interfaces que la infra implementa)
│   │   └── repositories.py   ← TicketRepository, UserRepository, SearchPort, etc.
│   ├── use_cases/             ← Lógica de negocio pura, un archivo por caso de uso
│   │   ├── create_ticket.py
│   │   ├── update_ticket.py
│   │   ├── close_ticket.py
│   │   ├── search_tickets.py
│   │   ├── add_comment.py
│   │   └── upload_attachment.py
│   └── exceptions.py          ← Errores de dominio con código y contexto
├── infrastructure/            ← Implementaciones concretas de los ports
│   ├── database/
│   │   ├── models.py          ← SQLAlchemy ORM (indexes, ARRAY, relationships)
│   │   ├── repositories/      ← Postgres repos → implementan domain ports
│   │   └── migrations/        ← Alembic (versioned)
│   ├── cache/                 ← Redis adapter (get/set/delete/increment)
│   ├── messaging/             ← Kafka producer + consumers
│   ├── search/                ← Elasticsearch adapter (index/search/delete)
│   └── storage/               ← S3/MinIO adapter (upload/presigned URL/delete)
├── api/
│   ├── v1/routes/             ← Flask-RESTX namespaces (endpoints delegados a use cases)
│   │   ├── tickets.py         ← /api/v1/tickets/ (CRUD, close, search, comments)
│   │   └── users.py           ← /api/v1/users/ (CRUD)
│   ├── v1/schemas/            ← Request/Response models para Swagger
│   └── middleware/            ← Error handlers globales, rate limiting por IP
├── core/
│   ├── config.py              ← pydantic-settings (validación de env vars al arranque)
│   ├── container.py           ← Inyección de dependencias manual (sin framework DI)
│   └── logging.py             ← structlog (JSON structured logging)
├── static/                    ← Assets de la Operator UI
│   ├── app.js                 ← Lógica del frontend (vanilla JS, sin frameworks)
│   └── styles.css             ← Estilos (vanilla CSS, responsive)
├── templates/
│   └── index.html             ← Template Jinja2 para la UI
├── main.py                    ← Application Factory (create_app)
└── seed.py                    ← Script de seeding para datos iniciales
```

## Operator UI

FlowDesk incluye una interfaz web integrada servida directamente por Flask en la ruta raíz (`/`). La UI permite a los operadores gestionar el sistema sin necesidad de herramientas externas como Postman o curl.

### Funcionalidades de la UI

- **Dashboard con métricas** — Contadores en tiempo real de tickets open, in progress, closed y total de usuarios.
- **Gestión de tickets** — Crear tickets con título, descripción, prioridad, creator y tags. Ver la lista completa, cerrar o eliminar tickets.
- **Panel de detalle** — Al seleccionar un ticket, se abre un panel lateral con la información completa, hilo de comentarios y formulario para agregar nuevos comentarios.
- **Gestión de usuarios** — Crear usuarios con email, nombre y rol (customer, agent, admin). Ver todos los usuarios registrados.
- **Búsqueda** — Barra de búsqueda que consulta Elasticsearch para encontrar tickets por contenido.
- **Health status** — Indicador en el sidebar que muestra el estado de la API y la conexión con Redis.
- **Navegación por tabs** — Cambiar entre la vista de Tickets y Users sin recargar la página.

## Decisiones de Diseño

- **Hexagonal Architecture (Ports & Adapters):** El dominio no importa NADA de infraestructura. Esto permite cambiar PostgreSQL por otro motor, o Elasticsearch por otro servicio de búsqueda, sin tocar la lógica de negocio.

- **Kafka para eventos:** Los eventos de tickets (created/updated/closed) son asincrónicos por naturaleza. Kafka garantiza entrega, permite replay, y desacopla los consumers (notificaciones, auditoría) del flujo principal.

- **Elasticsearch con boosted fields:** La búsqueda usa `multi_match` con boost en título (×3) y descripción (×2), con `fuzziness: AUTO` para tolerar errores tipográficos.

- **Redis para rate limiting:** Usa `INCR` atómico con TTL para rate limiting por IP. Si Redis cae, las requests pasan (graceful degradation).

- **Domain Exceptions con contexto:** Cada error lleva un `code` y datos relevantes (IDs, payloads) para logging estructurado y respuestas HTTP precisas.

- **No ORM en el dominio:** Las entidades son dataclasses puros. Los repositories hacen la traducción ORM ↔ Entity, manteniendo el dominio limpio.

- **Inyección de dependencias manual:** El `container.py` actúa como composition root sin frameworks de DI. Cada request obtiene su session y repositories frescos, garantizando aislamiento.

- **Vanilla JS para la UI:** La interfaz del operador usa JavaScript vanilla sin frameworks (React, Vue, etc.), manteniendo zero build steps y cero dependencias de frontend.

## Cómo correr el proyecto

### Requisitos

- Docker y Docker Compose (para el stack completo)
- Python 3.11+ (para desarrollo local o demo mode)

### Modo Demo (sin Docker, sin servicios externos)

La forma más rápida de explorar FlowDesk. Levanta la API completa con mocks in-memory para todos los servicios (PostgreSQL, Redis, Elasticsearch, Kafka, S3):

```bash
# Crear entorno virtual e instalar
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

pip install -e .

# Correr el demo server
python run_demo.py
```

Se crean 2 usuarios y 3 tickets de ejemplo automáticamente. La app estará disponible en:

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000/` | Operator UI |
| `http://localhost:8000/swagger/` | Swagger UI (docs interactivos) |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/api/v1/tickets/` | API de tickets |
| `http://localhost:8000/api/v1/users/` | API de usuarios |

### Con Docker (stack completo)

```bash
# Levantar todo (PostgreSQL, Redis, Elasticsearch, Kafka, MinIO, API, Consumers)
cd docker
docker-compose up -d

# Verificar que está corriendo
curl http://localhost:8000/health

# Ver Swagger UI
# Abrir en navegador: http://localhost:8000/swagger/
```

### Desarrollo local

```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Instalar dependencias (incluye dev tools)
pip install -e ".[dev]"

# Copiar configuración
cp .env.example .env

# Levantar servicios (PostgreSQL, Redis, etc.) con Docker
cd docker
docker-compose up -d db cache search kafka minio

# Ejecutar migraciones
alembic upgrade head

# Correr la API
flask --app app.main:create_app run --debug --port 8000
```

## Tests

```bash
# Correr todos los tests unitarios
pytest tests/unit/ -v

# Con cobertura
pytest tests/unit/ -v --cov=app --cov-report=term-missing

# Solo un test específico
pytest tests/unit/test_create_ticket.py -v
```

Los tests unitarios no requieren servicios externos — usan mocks para todas las dependencias de infraestructura (repositories, search, cache, broker, storage).

### CI/CD

El pipeline de GitHub Actions (`.github/workflows/ci.yml`) corre automáticamente en cada push a `main`/`develop` y en PRs:

1. **Lint** — Ruff verifica el estilo y errores comunes.
2. **Unit Tests** — pytest con cobertura sobre todos los tests en `tests/unit/`.

Los servicios de PostgreSQL y Redis se levantan como service containers en el runner de GitHub Actions.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Operator UI (interfaz web) |
| `GET` | `/health` | Health check (estado de la API y Redis) |
| `GET` | `/swagger/` | Swagger UI (documentación interactiva) |
| `GET` | `/api/v1/tickets/` | Listar tickets (filtrable por status y assignee) |
| `POST` | `/api/v1/tickets/` | Crear ticket |
| `GET` | `/api/v1/tickets/<id>` | Obtener ticket por ID |
| `PUT` | `/api/v1/tickets/<id>` | Actualizar ticket |
| `DELETE` | `/api/v1/tickets/<id>` | Eliminar ticket |
| `POST` | `/api/v1/tickets/<id>/close` | Cerrar ticket |
| `GET` | `/api/v1/tickets/<id>/comments` | Listar comentarios de un ticket |
| `POST` | `/api/v1/tickets/<id>/comments` | Agregar comentario |
| `GET` | `/api/v1/tickets/search?q=...` | Búsqueda full-text |
| `GET` | `/api/v1/users/` | Listar usuarios |
| `POST` | `/api/v1/users/` | Crear usuario |
| `GET` | `/api/v1/users/<id>` | Obtener usuario por ID |

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Entorno de ejecución | `development` |
| `FLASK_DEBUG` | Modo debug (1/0) | `1` |
| `SECRET_KEY` | Clave secreta de Flask | — |
| `DATABASE_URL` | Connection string de PostgreSQL | — |
| `REDIS_URL` | Connection string de Redis | — |
| `ELASTICSEARCH_URL` | URL del cluster de Elasticsearch | — |
| `KAFKA_BOOTSTRAP_SERVERS` | Dirección del broker Kafka | — |
| `AWS_ACCESS_KEY_ID` | Credencial de acceso S3/MinIO | — |
| `AWS_SECRET_ACCESS_KEY` | Credencial secreta S3/MinIO | — |
| `AWS_S3_BUCKET` | Nombre del bucket para attachments | `flowdesk-attachments` |
| `AWS_S3_ENDPOINT_URL` | URL del endpoint S3 (MinIO local) | — |
| `AWS_REGION` | Región AWS | `us-east-1` |
| `RATE_LIMIT_PER_MINUTE` | Máximo de requests por IP por minuto | `60` |

Consultar `.env.example` para una configuración de referencia completa.

## Servicios Docker

| Servicio | Imagen | Puerto | Propósito |
|----------|--------|--------|-----------|
| `api` | Build local | 8000 | API Flask + Operator UI |
| `notification-consumer` | Build local | — | Consumer Kafka para notificaciones |
| `audit-consumer` | Build local | — | Consumer Kafka para auditoría |
| `db` | postgres:16-alpine | 5432 | Base de datos principal |
| `cache` | redis:7-alpine | 6379 | Caché y rate limiting |
| `search` | elasticsearch:8.12.0 | 9200 | Motor de búsqueda full-text |
| `kafka` | confluentinc/cp-kafka:7.6.0 | 9092 | Message broker (KRaft, sin Zookeeper) |
| `minio` | minio/minio:latest | 9000, 9001 | Almacenamiento de archivos S3-compatible |

---

*Built with senior-level engineering practices: hexagonal architecture, domain-driven design, event-driven messaging, and comprehensive testing.*

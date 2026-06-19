# FlowDesk

> Sistema de gestión de tickets y soporte interno con búsqueda inteligente, eventos en tiempo real y arquitectura hexagonal.

## Stack

| Layer | Technology |
|-------|-----------|
| **API** | Python 3.11, Flask 3, Flask-RESTX (Swagger auto) |
| **ORM & Migrations** | SQLAlchemy 2, Alembic |
| **Database** | PostgreSQL 16 |
| **Search** | Elasticsearch 8 (full-text, fuzzy, boosted fields) |
| **Messaging** | Apache Kafka (KRaft mode, no Zookeeper) |
| **Cache & Rate Limiting** | Redis 7 |
| **File Storage** | AWS S3 / MinIO |
| **Containerization** | Docker, Docker Compose |
| **CI/CD** | GitHub Actions |
| **Testing** | pytest + pytest-cov |

## Arquitectura

```
Cliente HTTP
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

### Estructura del Proyecto (Hexagonal Architecture)

```
app/
├── domain/                    ← Puro Python. CERO dependencias externas
│   ├── entities/              ← Dataclasses: Ticket, User, Comment, Attachment
│   ├── ports/                 ← Protocolos/ABCs (interfaces)
│   ├── use_cases/             ← Lógica de negocio pura
│   └── exceptions.py          ← Errores de dominio con contexto
├── infrastructure/            ← Implementaciones concretas
│   ├── database/
│   │   ├── models.py          ← SQLAlchemy ORM (indexes, ARRAY, relationships)
│   │   ├── repositories/      ← Postgres repos → implementan domain ports
│   │   └── migrations/        ← Alembic (versioned)
│   ├── cache/                 ← Redis adapter
│   ├── messaging/             ← Kafka producer + consumers
│   ├── search/                ← Elasticsearch adapter
│   └── storage/               ← S3/MinIO adapter
├── api/
│   ├── v1/routes/             ← Flask-RESTX namespaces (thin endpoints)
│   ├── v1/schemas/            ← Request/Response models para Swagger
│   └── middleware/            ← Error handlers, rate limiting
└── core/
    ├── config.py              ← pydantic-settings (validación al arranque)
    ├── container.py           ← Inyección de dependencias manual
    └── logging.py             ← structlog (JSON structured)
```

## Decisiones de Diseño

- **Hexagonal Architecture (Ports & Adapters):** El dominio no importa NADA de infraestructura. Esto permite cambiar PostgreSQL por otro motor, o Elasticsearch por otro servicio de búsqueda, sin tocar la lógica de negocio.

- **Kafka para eventos:** Los eventos de tickets (created/updated/closed) son asincrónicos por naturaleza. Kafka garantiza entrega, permite replay, y desacopla los consumers (notificaciones, auditoría) del flujo principal.

- **Elasticsearch con boosted fields:** La búsqueda usa `multi_match` con boost en título (×3) y descripción (×2), con `fuzziness: AUTO` para tolerar errores tipográficos.

- **Redis para rate limiting:** Usa `INCR` atómico con TTL para rate limiting por IP. Si Redis cae, las requests pasan (graceful degradation).

- **Domain Exceptions con contexto:** Cada error lleva un `code` y datos relevantes (IDs, payloads) para logging estructurado y respuestas HTTP precisas.

- **No ORM en el dominio:** Las entidades son dataclasses puros. Los repositories hacen la traducción ORM ↔ Entity, manteniendo el dominio limpio.

## Cómo correr el proyecto

### Requisitos

- Docker y Docker Compose
- Python 3.11+ (para desarrollo local)

### Con Docker (recomendado)

```bash
# Levantar todo el stack (PostgreSQL, Redis, Elasticsearch, Kafka, MinIO, API, Consumers)
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

# Instalar dependencias
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

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/swagger/` | Swagger UI |
| `GET` | `/api/v1/tickets/` | List tickets (filterable) |
| `POST` | `/api/v1/tickets/` | Create ticket |
| `GET` | `/api/v1/tickets/<id>` | Get ticket by ID |
| `PUT` | `/api/v1/tickets/<id>` | Update ticket |
| `DELETE` | `/api/v1/tickets/<id>` | Delete ticket |
| `POST` | `/api/v1/tickets/<id>/close` | Close ticket |
| `GET` | `/api/v1/tickets/<id>/comments` | List comments |
| `POST` | `/api/v1/tickets/<id>/comments` | Add comment |
| `GET` | `/api/v1/tickets/search?q=...` | Full-text search |
| `GET` | `/api/v1/users/` | List users |
| `POST` | `/api/v1/users/` | Create user |
| `GET` | `/api/v1/users/<id>` | Get user |

---

*Built with senior-level engineering practices: hexagonal architecture, domain-driven design, event-driven messaging, and comprehensive testing.*

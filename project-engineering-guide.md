# Guía de Ingeniería de Software — Proyectos Python & React
> Referencia técnica para construir proyectos que demuestren criterio de Senior Engineer  
> Alineada a: **JBS Dev (Python/React Full Stack)** y **Gorilla Logic (Senior Python Engineer)**

---

## 0. Filosofía base antes de escribir código

Un proyecto de portafolio no es un CRUD con README. Es evidencia de cómo piensas.

Cuando un Tech Lead lo revisa, no busca que funcione. Busca respuestas a estas preguntas:

- ¿Entiende los límites de su propio diseño?
- ¿Tomó decisiones conscientes o solo copió un tutorial?
- ¿Puedo incorporar este código sin que rompa lo que ya tenemos?
- ¿Qué tan caro sería cambiar esto en 6 meses?

Escribe código como si el que lo va a mantener sabe dónde vives.

---

## 1. Principios de ingeniería aplicados con criterio

### 1.1 SOLID

No memorices la sigla. Entiende qué problema resuelve cada letra.

| Principio | Señal de que lo estás violando | Corrección concreta |
|---|---|---|
| **S** — Single Responsibility | Una clase/función hace fetch, valida y formatea | Separar en capas: service, validator, serializer |
| **O** — Open/Closed | Cada nuevo tipo de usuario requiere editar `if/elif` central | Usar estrategias, factories o polimorfismo |
| **L** — Liskov | Subclases que lanzan excepciones que el padre no lanza | Revisar contratos, no solo herencia |
| **I** — Interface Segregation | Implementas métodos con `pass` o `raise NotImplementedError` | Interfaces pequeñas y enfocadas |
| **D** — Dependency Inversion | Instancias concretas hardcodeadas dentro de clases | Inyectar dependencias, programar contra abstracciones |

**Regla práctica:** si tienes que leer toda la clase para entender qué hace una función, S está roto.

---

### 1.2 DRY — Don't Repeat Yourself

DRY no significa "nunca escribas lo mismo dos veces".  
Significa **no dupliques conocimiento con representaciones divergentes**.

```python
# ❌ MAL: lógica duplicada que puede divergir
def validate_user_email(email: str) -> bool:
    return "@" in email and "." in email

def validate_admin_email(email: str) -> bool:
    return "@" in email and "." in email  # Copia exacta. Si cambia la regla, se rompe en un solo lugar.

# ✅ BIEN: la regla de negocio vive en un lugar
def is_valid_email(email: str) -> bool:
    import re
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email))
```

**Cuidado:** el over-DRY es tan dañino como el under-DRY. No abstraigas antes de tener al menos 3 casos reales.

---

### 1.3 KISS & YAGNI

- **KISS:** La solución más simple que resuelve el problema real es la mejor solución.
- **YAGNI:** No construyas lo que podrías necesitar. Construye lo que necesitas ahora.

```python
# ❌ MAL: "Por si acaso lo necesitamos después..."
class UserProcessor:
    def __init__(self, strategy=None, plugin_registry=None, event_bus=None):
        ...  # Nada de esto está siendo usado todavía

# ✅ BIEN: resuelve el problema actual
class UserProcessor:
    def process(self, user: User) -> ProcessedUser:
        ...
```

La flexibilidad que nadie usa tiene un costo: complejidad que todos cargan.

---

### 1.4 Separación de responsabilidades

En Python backend, la separación mínima profesional es:

```
┌─────────────────┐
│   API Layer     │  ← Maneja HTTP: rutas, request/response, auth
├─────────────────┤
│  Service Layer  │  ← Lógica de negocio. No sabe de HTTP ni de DB
├─────────────────┤
│ Repository Layer│  ← Acceso a datos. No sabe de negocio
├─────────────────┤
│  Domain/Models  │  ← Entidades. No dependen de nada externo
└─────────────────┘
```

Una función de servicio no debería importar `Flask`, `request`, ni `Response`.  
Un endpoint no debería contener lógica de negocio.

---

### 1.5 Bajo acoplamiento, alta cohesión

- **Acoplamiento:** cuánto sabe un módulo de los internos de otro.
- **Cohesión:** qué tan relacionadas entre sí están las responsabilidades de un módulo.

**Señales de alto acoplamiento:**
- Cambias una línea en `user_service.py` y se rompe `order_service.py`
- Un módulo importa directamente la implementación concreta de otro

**Corrección:**
```python
# En lugar de esto:
from app.infrastructure.postgres.user_repo import PostgresUserRepo

# Programa contra esto (abstracción):
from app.domain.ports import UserRepository  # interfaz/protocolo
```

---

### 1.6 Arquitectura orientada al cambio

Diseña asumiendo que:
- El motor de base de datos puede cambiar
- La lógica de negocio evolucionará
- El framework puede ser reemplazado

**Aplica esto con Ports & Adapters (Hexagonal Architecture):**

```
app/
├── domain/           ← Puro Python. Cero dependencias externas
│   ├── entities/
│   ├── ports/        ← Interfaces/Protocolos (lo que el dominio necesita)
│   └── use_cases/
├── infrastructure/   ← Implementaciones concretas (DB, cache, APIs externas)
│   ├── postgres/
│   ├── redis/
│   └── kafka/
└── api/              ← Entrypoint HTTP (Flask/FastAPI)
    ├── routes/
    └── schemas/
```

El dominio no importa nada de `infrastructure/`. Jamás.

---

### 1.7 Manejo correcto de errores

Errores no son excepciones de Python. Son parte del contrato de tu sistema.

```python
# ❌ MAL: atrapa todo y lo silencia
try:
    result = process_order(order_id)
except Exception:
    return {"error": "Something went wrong"}

# ✅ BIEN: errores específicos, con contexto, loggeados apropiadamente
class OrderNotFoundError(DomainError):
    pass

class InsufficientInventoryError(DomainError):
    pass

# En la capa de API:
@app.errorhandler(OrderNotFoundError)
def handle_not_found(e: OrderNotFoundError):
    logger.warning("Order not found", extra={"order_id": e.order_id})
    return jsonify({"error": "Order not found", "code": "ORDER_NOT_FOUND"}), 404
```

**Reglas:**
- Define excepciones de dominio propias. No uses `ValueError` para lógica de negocio.
- Loggea con contexto (IDs, payloads relevantes), nunca strings genéricos.
- No atrapes lo que no puedes manejar. Deja que suba.
- Distingue entre errores operacionales (esperados) y errores de programación (bugs).

---

### 1.8 Tests como parte del diseño (no como afterthought)

Si escribes el test después, estás verificando. Si lo escribes antes, estás diseñando.

**Pirámide de testing aplicada:**

```
        [E2E]          ← Pocos. Costosos. Solo flujos críticos.
      [Integration]    ← Moderados. Prueban capas juntas (repo + DB real).
    [Unit Tests]       ← Muchos. Rápidos. Prueban lógica de negocio aislada.
```

```python
# tests/unit/test_order_service.py
def test_create_order_fails_when_insufficient_inventory():
    # Arrange
    repo = MockOrderRepository(available_stock=0)
    service = OrderService(repo)
    
    # Act & Assert
    with pytest.raises(InsufficientInventoryError):
        service.create_order(product_id="SKU-001", quantity=5)
```

**Nombra tus tests como documentación:**
`test_[unit]_[condition]_[expected_behavior]`

---

## 2. Estructura de proyecto — Python Backend (Flask / FastAPI)

```
project-name/
├── app/
│   ├── domain/
│   │   ├── entities/          # Dataclasses o Pydantic models puros
│   │   ├── ports/             # Protocolos/ABCs: UserRepository, CachePort
│   │   └── use_cases/         # Lógica de negocio. Sin imports de infra.
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── models.py      # SQLAlchemy ORM models
│   │   │   ├── migrations/    # Alembic
│   │   │   └── repositories/  # Implementación concreta de ports
│   │   ├── cache/             # Redis adapter
│   │   ├── messaging/         # Kafka producers/consumers
│   │   └── search/            # Elasticsearch adapter
│   ├── api/
│   │   ├── v1/
│   │   │   ├── routes/        # Blueprints o routers
│   │   │   └── schemas/       # Pydantic/Marshmallow: request/response
│   │   └── middleware/        # Auth, logging, error handlers
│   └── core/
│       ├── config.py          # Settings via pydantic-settings o dynaconf
│       ├── container.py       # Dependency injection container
│       └── logging.py         # Configuración de logging estructurado
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions
├── alembic.ini
├── pyproject.toml             # Dependencias + herramientas (ruff, mypy, pytest)
└── README.md
```

---

## 3. Estructura de proyecto — React / Next.js Frontend

```
frontend/
├── src/
│   ├── app/                   # Next.js App Router (o pages/ si Pages Router)
│   ├── components/
│   │   ├── ui/                # Componentes genéricos (Button, Input, Modal)
│   │   └── features/          # Componentes de dominio (OrderCard, UserProfile)
│   ├── hooks/                 # Custom hooks: useAuth, useOrderList
│   ├── services/              # Llamadas HTTP. Nada de fetch directo en componentes.
│   │   └── api/
│   │       ├── client.ts      # Axios/fetch configurado con interceptors
│   │       └── orders.ts      # Métodos específicos por dominio
│   ├── store/                 # Redux Toolkit o Zustand
│   │   ├── slices/
│   │   └── index.ts
│   ├── types/                 # TypeScript interfaces y tipos globales
│   ├── utils/                 # Funciones puras sin side effects
│   └── lib/                   # Helpers de terceros (validación, fecha, etc.)
├── tests/
│   ├── unit/
│   └── integration/
├── public/
├── .github/
│   └── workflows/
│       └── ci.yml
├── tsconfig.json
├── vite.config.ts             # O next.config.ts
└── README.md
```

---

## 4. Stack técnico alineado a los puestos target

### Backend (Python)

| Tecnología | Uso | Por qué importa en estos puestos |
|---|---|---|
| **Python 3.11+** | Core | Gorilla Logic especifica 3.10–3.12 |
| **Flask + Flask-RESTX** | API REST | Requerido explícitamente en Gorilla Logic |
| **FastAPI** | Alternativa moderna | Señal de criterio técnico actualizado |
| **SQLAlchemy + Alembic** | ORM + Migraciones | Requerido en Gorilla Logic |
| **PostgreSQL** | Base de datos | Ambos puestos lo requieren |
| **Redis** | Caché y task queues | Nice-to-have en Gorilla Logic |
| **Apache Kafka** | Event-driven | Requerido en Gorilla Logic |
| **Elasticsearch** | Search | Requerido en Gorilla Logic |
| **Docker** | Containerización | Ambos puestos |
| **AWS (S3, EC2, EKS)** | Cloud | Ambos puestos (CDK en JBS Dev) |
| **pytest + pytest-cov** | Testing | Obligatorio en cualquier proyecto serio |
| **Pydantic v2** | Validación y schemas | Estándar actual |
| **Ruff** | Linting rápido | Reemplaza flake8 + isort |
| **mypy** | Type checking | Señal de código serio |

### Frontend (React)

| Tecnología | Uso | Por qué importa |
|---|---|---|
| **React 18 + TypeScript** | Core | Ambos puestos |
| **Next.js 14+** | Framework | JBS Dev lo menciona explícitamente |
| **Redux Toolkit** | State management | Gorilla Logic lo usa (junto a Vite) |
| **React Query / TanStack Query** | Server state | Estándar moderno en roles senior |
| **Tailwind CSS** | Estilos | Velocidad + consistencia |
| **Vitest / Jest + Testing Library** | Tests | No negociable en un portafolio senior |
| **ESLint + Prettier** | Calidad de código | |

---

## 5. Configuración y dependencias explícitas

### pyproject.toml (Python)

```toml
[project]
name = "your-project"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "flask>=3.0",
    "flask-restx>=1.3",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "pydantic>=2.5",
    "pydantic-settings>=2.1",
    "psycopg2-binary>=2.9",
    "redis>=5.0",
    "kafka-python>=2.0",
    "elasticsearch>=8.0",
]

[tool.ruff]
line-length = 88
select = ["E", "W", "F", "I", "B", "C4", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=app --cov-report=term-missing --cov-fail-under=80"
```

### Inyección de dependencias (sin framework adicional)

```python
# app/core/container.py
from app.domain.ports import UserRepository, CachePort
from app.infrastructure.database.repositories import PostgresUserRepository
from app.infrastructure.cache.redis_cache import RedisCache

class Container:
    def __init__(self):
        self._user_repo: UserRepository = PostgresUserRepository()
        self._cache: CachePort = RedisCache()

    @property
    def user_repository(self) -> UserRepository:
        return self._user_repo

    @property
    def cache(self) -> CachePort:
        return self._cache

container = Container()
```

---

## 6. Patrones específicos para cada capa

### 6.1 API Layer — Flask

```python
# app/api/v1/routes/orders.py
from flask import Blueprint, request, jsonify
from app.core.container import container
from app.domain.use_cases.create_order import CreateOrderUseCase
from app.api.v1.schemas.order import CreateOrderSchema, OrderResponseSchema
from app.domain.exceptions import InsufficientInventoryError

orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")

@orders_bp.post("/")
def create_order():
    schema = CreateOrderSchema()
    data = schema.load(request.json)  # Valida y deserializa

    use_case = CreateOrderUseCase(
        order_repo=container.order_repository,
        cache=container.cache,
    )

    try:
        order = use_case.execute(data)
        return OrderResponseSchema().dump(order), 201
    except InsufficientInventoryError as e:
        return jsonify({"error": str(e), "code": "INSUFFICIENT_INVENTORY"}), 422
```

### 6.2 Use Case Layer

```python
# app/domain/use_cases/create_order.py
from dataclasses import dataclass
from app.domain.entities import Order, OrderItem
from app.domain.ports import OrderRepository, CachePort
from app.domain.exceptions import InsufficientInventoryError

@dataclass
class CreateOrderInput:
    user_id: str
    items: list[dict]

class CreateOrderUseCase:
    def __init__(self, order_repo: OrderRepository, cache: CachePort):
        self._repo = order_repo
        self._cache = cache

    def execute(self, input: CreateOrderInput) -> Order:
        # Lógica de negocio aquí. Sin Flask. Sin SQLAlchemy. Solo Python.
        for item in input.items:
            stock = self._cache.get(f"stock:{item['product_id']}") or \
                    self._repo.get_stock(item['product_id'])
            if stock < item['quantity']:
                raise InsufficientInventoryError(product_id=item['product_id'])

        order = Order.create(user_id=input.user_id, items=input.items)
        self._repo.save(order)
        return order
```

### 6.3 Kafka Producer/Consumer (Gorilla Logic)

```python
# app/infrastructure/messaging/kafka_producer.py
from kafka import KafkaProducer
from app.domain.ports import MessageBroker
import json

class KafkaMessageBroker(MessageBroker):
    def __init__(self, bootstrap_servers: list[str]):
        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def publish(self, topic: str, message: dict) -> None:
        future = self._producer.send(topic, value=message)
        future.get(timeout=10)  # Espera confirmación, no dispara y olvida

    def close(self) -> None:
        self._producer.flush()
        self._producer.close()
```

### 6.4 React — Separación servicio/componente

```typescript
// src/services/api/orders.ts
import { apiClient } from "./client";
import type { Order, CreateOrderPayload } from "@/types/order";

export const ordersService = {
  getAll: (): Promise<Order[]> =>
    apiClient.get("/orders").then((res) => res.data),

  create: (payload: CreateOrderPayload): Promise<Order> =>
    apiClient.post("/orders", payload).then((res) => res.data),

  cancel: (orderId: string): Promise<void> =>
    apiClient.delete(`/orders/${orderId}`),
};
```

```typescript
// src/hooks/useOrders.ts — Server state con React Query
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ordersService } from "@/services/api/orders";

export function useOrders() {
  return useQuery({
    queryKey: ["orders"],
    queryFn: ordersService.getAll,
    staleTime: 1000 * 60 * 5,
  });
}

export function useCancelOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ordersService.cancel,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["orders"] }),
  });
}
```

---

## 7. CI/CD con GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: user
          POSTGRES_PASSWORD: password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint (Ruff)
        run: ruff check .

      - name: Type check (mypy)
        run: mypy app/

      - name: Run tests
        run: pytest --cov=app --cov-fail-under=80

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run test
      - run: npm run build
```

---

## 8. Docker (base profesional)

```dockerfile
# Dockerfile (multi-stage build)
FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

FROM base AS builder
COPY pyproject.toml .
RUN pip install --no-cache-dir build && \
    pip wheel --no-cache-dir --wheel-dir /wheels -e .

FROM base AS production
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY app/ ./app/
EXPOSE 8000
CMD ["gunicorn", "app.main:create_app()", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/appdb
      REDIS_URL: redis://cache:6379/0
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_started

  db:
    image: postgres:16-alpine
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD", "pg_isready"]
      interval: 10s

  cache:
    image: redis:7-alpine

volumes:
  postgres_data:
```

---

## 9. README que vende el proyecto

El README es la primera impresión. Trátatelo como un documento de producto, no como notas personales.

### Estructura mínima profesional

```markdown
# Nombre del Proyecto

> Una línea que explica qué hace, para quién, y qué problema resuelve.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, Flask 3, SQLAlchemy 2 |
| Database | PostgreSQL 16, Redis 7 |
| Frontend | React 18, TypeScript, Next.js 14 |
| Infra | Docker, GitHub Actions, AWS |

## Arquitectura

[Diagrama o descripción de las capas y flujo de datos]

## Decisiones de diseño

- **Por qué Hexagonal Architecture**: permite intercambiar la implementación de persistencia sin tocar el dominio.
- **Por qué Kafka para X**: los eventos son asincrónicos por naturaleza. Kafka garantiza entrega y permite replay.
- **Por qué no ORM en el dominio**: el dominio no debería saber que existe una base de datos.

## Cómo correr el proyecto

\`\`\`bash
docker-compose up -d
\`\`\`

## Tests

\`\`\`bash
pytest --cov=app -v
\`\`\`

Cobertura actual: 84%

## Estructura del proyecto

[Árbol de directorios con descripción de cada capa]
```

**Regla:** La sección "Decisiones de diseño" es la que diferencia un portafolio junior de uno senior. Explica el *por qué*, no el *qué*.

---

## 10. Checklist antes de publicar el proyecto

### Código

- [ ] Sin credenciales, API keys ni passwords en el código
- [ ] Variables de entorno documentadas en `.env.example`
- [ ] Sin prints de debugging
- [ ] Sin código comentado (usa git para eso)
- [ ] Tipos anotados en todo el código Python (`mypy` pasa sin errores)
- [ ] TypeScript sin `any` explícito sin justificación

### Arquitectura

- [ ] El dominio no importa nada de infraestructura
- [ ] Cada capa tiene una responsabilidad clara y documentada
- [ ] Los errores tienen tipos propios y mensajes útiles
- [ ] Los tests cubren al menos los casos de negocio principales (no solo happy path)

### Infraestructura

- [ ] Docker Compose levanta el proyecto completo con un comando
- [ ] CI/CD corre en cada PR y falla si los tests fallan
- [ ] Migraciones de base de datos están incluidas y son reproducibles

### README

- [ ] Explica el problema que resuelve, no solo cómo correrlo
- [ ] Incluye las decisiones de arquitectura y su justificación
- [ ] Stack visible y actualizado
- [ ] Instrucciones de setup funcionan desde cero (pruébalas tú mismo)

---

## 11. Lo que diferencia un portafolio junior de uno senior

| Portafolio Junior | Portafolio Senior |
|---|---|
| "Hice un CRUD con Flask" | "Implementé arquitectura hexagonal separando dominio de infraestructura" |
| Tests = 0 o tests que prueban que Flask funciona | Tests que documentan el comportamiento del negocio |
| Toda la lógica en el endpoint | Endpoints delgados, lógica en use cases |
| `except Exception: pass` | Jerarquía de errores de dominio con handlers específicos |
| Variables de entorno hardcodeadas | Config centralizada con validación al arranque |
| README con solo `pip install` | README con arquitectura, decisiones y trade-offs |
| Un solo branch `main` | Feature branches, PRs, CI que bloquea merges con fallos |
| Commits: "fix", "changes", "asdf" | Commits: `feat(orders): add inventory validation on order creation` |

---

*Última actualización: para puestos Senior Python/React — JBS Dev & Gorilla Logic, Costa Rica*

# Architecture

## System overview

```
Browser
  |
  |  REST (JSON)
  v
React + TypeScript frontend  (Vite, Tailwind CSS, port 3000)
  |
  |  nginx proxies /api to the backend service
  v
FastAPI backend  (Python, port 8000)
  |                     \
  | SQLAlchemy            \ HTTP (retain / recall)
  v                        v
PostgreSQL                Hindsight
operational state         long-term experiential memory
(suppliers, inventory,    (past disruptions, decisions,
 orders, cases, alerts,    approvals, outcomes,
 approvals)                supplier behaviour)
```

PostgreSQL holds current operational truth. Hindsight holds long-term
experience. The two are deliberately not mixed: no table in PostgreSQL stores
agent memory, and no long-term memory table is created anywhere in the schema.

## Backend layout

```
backend/
  main.py              FastAPI app, health, dashboard stats, memory and alerts
  agents/              one module per LangGraph agent node
  api/routes/          HTTP route handlers
  database/            engine, session factory, alembic migrations
  models/              SQLAlchemy ORM models
  services/            business logic shared by routes and agents
  hindsight/           thin client wrapper around the Hindsight SDK
  workflows/           LangGraph StateGraph definition and shared state
  utils/               settings, logging, API key guard
  scripts/             seed_data.py demo dataset
  tests/               pytest suite
```

## Agent workflow

`workflows/disruption_workflow.py` compiles a LangGraph `StateGraph` with eight
nodes. The first seven are the agents required by the specification; the eighth
is the human approval gate.

| # | Node | Responsibility |
|---|---|---|
| 1 | Supply Chain Monitoring | Collects supplier, inventory and order state |
| 2 | Disruption Detection | Confirms the event is a meaningful disruption |
| 3 | Inventory and Demand Analysis | Coverage days, stockout risk, supply gap |
| 4 | Impact Assessment | Days short, material value at risk, indirect penalty |
| 5 | Alternative Supplier and Mitigation | Hindsight recall plus supplier comparison |
| 6 | Alert and Response Planning | Builds the operational alert and response plan |
| 7 | Reviewer | Validates evidence, confidence and human-in-the-loop status |
| 8 | Human Approval Gatekeeper | Halts execution and persists state for approval |

Nodes are connected in a single linear pass. The gatekeeper never executes a
supply-chain action; it writes `pending_approval` to the database and stops.

### State

`workflows/state.py` defines `AgentState`, a `TypedDict` that every node reads
and writes. It carries the operational inputs (delay, coverage, demand), the
derived results (stockout risk, business impact, recommendation), the recalled
`hindsight_memories`, and the append-only `agent_trace` that powers the
explainability view.

## Data model

| Table | Contents |
|---|---|
| `suppliers` | lead time, reliability score, capabilities, location, status |
| `inventory_items` | quantity, daily demand, safety stock, reorder point, supplier link |
| `purchase_orders` | quantities, expected delivery, status, delay days |
| `disruption_cases` | active and resolved cases, analysis results, recommendation, outcome |
| `alerts` | generated alerts and read state |
| `approval_requests` | recommendation awaiting a human decision, notes, decided_at |

Migrations live in `backend/database/migrations` (Alembic). The initial
revision `82c2dc23c8ff` creates every table. `main.py` also calls
`create_all` on startup so a fresh container comes up on an empty database.

Order of operations for a fresh environment:

```bash
alembic upgrade head   # empty database only
python scripts/seed_data.py
```

If the tables already exist and were created by `create_all`, run
`alembic stamp head` instead of `upgrade`.

## Hindsight integration

The wrapper in `hindsight/client.py` exposes four functions:

- `retain(bank_id, content)` / `await aretain(...)` store one experience as text
- `recall(bank_id, query, limit)` / `await arecall(...)` return matching experiences

The async pair is what the API routes and agent nodes call; the sync pair
exists for scripts and tests. Both fail soft. If Hindsight is unreachable the
workflow continues with an empty history and logs a warning, so a memory
outage never blocks an incident.

Two details inside the wrapper matter for a correct integration:

- **Event loop.** The SDK's synchronous helpers call
  `loop.run_until_complete`, which raises `RuntimeError` when the caller is
  already inside the running uvicorn/LangGraph loop. The wrapper therefore
  drives the SDK's `aretain`/`arecall` methods on one private daemon event
  loop, so calls work identically from request handlers, from agent nodes and
  from scripts. Handlers and agent nodes await `aretain`/`arecall`, which run
  that blocking call on a worker thread and keep the application's event loop
  free.
- **Response shape.** The SDK answers with Pydantic objects (`RetainResponse`,
  `RecallResponse` with `RecallResult.text` and `scores.final`), while agents
  and routes expect plain `{"content", "relevance_score"}` dictionaries. The
  wrapper normalises both directions, so nothing outside it depends on SDK
  internals.

The server runs as `ghcr.io/vectorize-io/hindsight:latest` (see
`docker/README.md`), with its embedded pg0 database in a named volume.

Retention and recall happen at two points:

| Point | Function |
|---|---|
| `agents/mitigation.py` | recalls experience before building a recommendation |
| `POST /disruptions/{id}/resolve` | retains the full event, decision and outcome |

A retained experience is plain text built from real case fields: supplier,
disruption type, delay, the recommended action, the operator decision and the
recorded outcome.

### How experience changes the recommendation

The mitigation agent branches on whether recall returned anything:

| | No prior memory | Prior memory recalled |
|---|---|---|
| Confidence | 0.76 | 0.94 |
| Risk level | Medium | Low |
| Action shape | emergency secondary purchase order | activate validated contingency protocol |
| Rationale | states that no history exists | quotes the recalled experience |

`GET /disruptions/{id}/memory` and `GET /memory` expose the same content to the
UI, and every agent trace entry labels whether a value came from SQL, from
Hindsight or from the agent itself.

## Explainability

Each node appends an object with `agent`, `timestamp`, `analysis`,
`conclusions` and `data_used` to `agent_trace`. The trace is stored on the case
and served by `GET /agents/{case_id}/trace`. The detail page renders it as a
timeline, so the four required sources stay distinguishable:

1. Current SQL data (coverage, impact, supplier comparison)
2. Retrieved Hindsight memories (count and content)
3. Agent conclusions (proposed action, confidence)
4. Human decision (the operator entry appended on approve or reject)

## API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/suppliers`, `/inventory`, `/purchase-orders` | operational data |
| GET | `/disruptions`, `/disruptions/{id}` | cases |
| POST | `/disruptions/simulate` | start a controlled disruption |
| POST | `/disruptions/{id}/approve` | human approval |
| POST | `/disruptions/{id}/reject` | human rejection |
| POST | `/disruptions/{id}/resolve` | record outcome, retain in Hindsight |
| GET | `/disruptions/{id}/memory` | memories attached to the case |
| GET | `/agents/{case_id}/trace` | agent reasoning |
| GET | `/dashboard/stats` | dashboard counters computed from SQL |
| GET | `/memory` | resolved cases plus Hindsight recall |
| GET | `/alerts`, POST `/alerts/{id}/read` | alert stream |

Request bodies are validated with Pydantic field constraints: unknown enum
values, negative delays, unknown supplier identifiers and over-long notes are
rejected with 422 or 404.

## Security

- Secrets are read from the environment through `utils/config.py`. Nothing is
  hardcoded and no credential reaches the frontend.
- `API_KEY` enables an opt-in `X-API-Key` guard on every state-changing
  endpoint (`utils/security.py`). It is disabled when unset, so local demos are
  unaffected. The frontend forwards `VITE_API_KEY` when it is set.
- Database and Hindsight configuration are never returned by any endpoint.
- CORS is restricted to the configured frontend origins.

## Deployment

`docker-compose.yml` starts four services on the `scm_network` bridge:
`frontend`, `backend`, `postgres`, `hindsight`. The backend waits for healthy
PostgreSQL **and** a healthy Hindsight, the frontend waits for a healthy
backend, and nginx proxies `/api` to `backend:8000` over the container network.
Health checks use Python probes (`python -c "urllib.request.urlopen(...)"`)
because neither `python:3.11-slim` nor the Hindsight image ships `curl` or
`wget`: PostgreSQL answers `pg_isready`, Hindsight answers `GET /health`
(readiness), the backend answers `GET /health`.

`docker/docker-compose.infra.yml` starts only PostgreSQL and Hindsight for
native development.

## Known limitations

- The LLM refinement in each agent is optional. Without `GOOGLE_API_KEY` the
  deterministic rule-based analysis is used, which keeps the demonstration
  reproducible and offline.
- Tests run against in-memory SQLite with a fake Hindsight client so the suite
  needs no external services. The production code paths are unchanged.
- Docker was not installed in the build environment, so the compose stack was
  verified statically (`scripts/validate_compose.py`, `docker compose config`
  in `scripts/verify.ps1`) rather than started end to end. The Hindsight image,
  environment variable names and health endpoint were checked against the
  upstream Hindsight installation and monitoring documentation.
- Hindsight itself needs an LLM key for fact extraction. Without
  `GOOGLE_API_KEY` the memory layer logs a warning per call and returns an
  empty history, so the workflow still runs.
- Data is simulated and labelled as such in the UI header and the simulator.

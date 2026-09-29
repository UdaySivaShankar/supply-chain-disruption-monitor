# Agentic AI Supply Chain Disruption Monitoring System

A production-style AI-powered supply chain disruption monitoring and mitigation platform built for hackathon demonstration.

## Project Idea

Supply chains are constantly hit by disruptions — supplier delays, port
blockages, quality rejects, sudden demand spikes. By the time a human analyst
notices, cross-references inventory, and decides what to do, the stockout has
already happened. Teams also keep re-solving the same problem: every new
incident is handled from scratch, with no memory of what worked last time.

**The idea:** an agentic AI system that watches the supply chain continuously,
detects disruptions as they happen, works out the business impact, and proposes
a concrete mitigation — while a human stays in control of the final decision,
and every resolved case makes the system smarter.

## Solution

The system is a full-stack application with a 7-agent LangGraph workflow and
long-term memory:

1. **Detection** — monitoring and detection agents continuously scan suppliers,
   inventory, and purchase orders, and confirm the disruption type and severity
   (a built-in simulator can inject realistic events such as a 10-day supplier
   delay).
2. **Analysis** — analysis agents compute inventory coverage days, stockout
   risk, financial exposure, and downstream impact on open purchase orders.
3. **Mitigation** — the mitigation agent compares alternative suppliers on
   lead time, cost, capacity, and risk, and produces a ranked recommendation
   with a full reasoning trace shown in the UI.
4. **Long-term memory (Hindsight)** — before recommending, the agent recalls
   similar past incidents from Hindsight; after a case is resolved, the
   experience (what was decided and how it turned out) is retained, so repeat
   incidents get recommendations informed by prior outcomes.
5. **Human-in-the-loop** — nothing executes automatically: every recommendation
   is presented for explicit human **Approve/Reject**, and only then can the
   case be marked resolved and fed back into memory.

State lives in PostgreSQL (suppliers, inventory, purchase orders, disruptions,
approval status), the React dashboard exposes detection, impact, memories, and
the approval controls, and the whole stack runs with Docker Compose. All data is
simulated and labelled as such.

## Documentation

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, agent workflow, data model, Hindsight integration, security |
| [docs/DEMO.md](docs/DEMO.md) | End-to-end demonstration instructions, including the learning demo |
| [docker/README.md](docker/README.md) | Docker layout and service networking |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Port 3000)                │
│         TypeScript + Tailwind CSS Dashboard                  │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────────────┐
│              FastAPI Backend (Port 8000)                     │
│         Python + LangGraph Agent Orchestration               │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
┌──────────▼──────────┐      ┌────────────▼───────────────────┐
│  PostgreSQL (5432)  │      │   Hindsight (Port 8888)        │
│  Operational State  │      │   Long-Term Agent Memory       │
│  - Suppliers        │      │   - Disruption Experiences     │
│  - Inventory        │      │   - Agent Decisions            │
│  - Purchase Orders  │      │   - Mitigation Outcomes        │
│  - Disruptions      │      │   - Supplier History           │
└─────────────────────┘      └────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Tailwind CSS |
| Backend | FastAPI + Python 3.11 |
| Agent Orchestration | LangGraph |
| LLM | Google Gemini (via langchain-google-genai) |
| Operational Database | PostgreSQL 16 |
| Long-Term Memory | Hindsight (`ghcr.io/vectorize-io/hindsight`) |
| Containerization | Docker + Docker Compose |

## Agent Workflow

The system uses a 7-node LangGraph workflow triggered when a disruption is detected:

1. **Supply Chain Monitoring** - Collects current state from the database
2. **Disruption Detection** - Confirms type and severity of the event
3. **Inventory and Demand Analysis** - Calculates coverage days and stockout risk
4. **Impact Assessment** - Determines business impact and financial exposure
5. **Alternative Supplier and Mitigation** - Recalls historical experiences from Hindsight, evaluates alternatives
6. **Alert and Response Planning** - Generates actionable alerts and response plan
7. **Reviewer** - Reviews all evidence before presenting for human approval

After human approval, resolved cases are retained in Hindsight for future reference.

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Google Gemini API key (optional but recommended for full LLM reasoning)

### Setup

1. Clone and configure:
```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

2. Start all services:
```bash
docker-compose up -d
```

3. Wait for services to be healthy (about 30 seconds), then seed demo data:
```bash
docker-compose exec backend python scripts/seed_data.py
```

4. Access the application:
   - Frontend Dashboard: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Hindsight Memory API: http://localhost:8888 (OpenAPI at `/docs`)
   - Hindsight Control Plane: http://localhost:9999

### Local Development

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env with local DB settings
alembic upgrade head      # fresh database only
# If tables already exist: alembic stamp head
python scripts/seed_data.py
uvicorn main:app --reload
```

**Docker only infrastructure (PostgreSQL + Hindsight) while running the apps natively:**
```bash
docker compose -f docker/docker-compose.infra.yml up -d
```

**Optional API authorization:**
Set `API_KEY` in `.env` to require an `X-API-Key` header on every
state-changing endpoint, and set `VITE_API_KEY` to the same value for the
frontend. Leave both empty for local development and demonstrations.

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | System health check |
| GET | /suppliers | List all suppliers |
| GET | /inventory | List inventory items |
| GET | /purchase-orders | List purchase orders |
| GET | /disruptions | List disruption cases |
| GET | /disruptions/{id} | Get disruption details |
| POST | /disruptions/simulate | Trigger a simulated disruption |
| POST | /disruptions/{id}/approve | Approve mitigation recommendation |
| POST | /disruptions/{id}/reject | Reject mitigation recommendation |
| POST | /disruptions/{id}/resolve | Mark resolved and retain in Hindsight |
| GET | /disruptions/{id}/memory | Get Hindsight memories for case |
| GET | /agents/{case_id}/trace | Get agent reasoning trace |
| GET | /dashboard/stats | Dashboard summary statistics |
| GET | /alerts | List all alerts |

## Running Tests

```bash
cd backend
pytest tests/ -v
```

The suite covers database operations, inventory calculations, disruption
detection, impact assessment, supplier comparison, Hindsight retain and
recall, the agent workflow, the approval workflow, every API endpoint, and an
end-to-end test that simulates a disruption, generates a recommendation,
approves it, records the outcome and verifies the experience is retained in
Hindsight. Tests use in-memory SQLite and a fake Hindsight client, so they need
no running services.

## Verification Script

Runs the full pre-delivery check: backend tests, frontend production build,
database migrations on a clean database, seed data, and compose validation.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1   # Windows
sh scripts/verify.sh                                          # macOS / Linux
```

## Command Line Demo

```bash
python scripts/run_demo.py --base-url http://localhost:8000
```

Triggers the two-event learning sequence against a running backend and prints
the confidence and memory comparison. See [docs/DEMO.md](docs/DEMO.md).

## Project Structure

```
hackathon_3.0/
  frontend/                 # React TypeScript dashboard
  backend/
    agents/                 # LangGraph agent node implementations
    api/routes/             # FastAPI route handlers
    database/
      connection.py         # Engine and session factory
      migrations/           # Alembic env, script template, versions/
    models/                 # SQLAlchemy ORM models
    services/               # Business logic services
    hindsight/              # Hindsight client wrapper
    workflows/              # LangGraph StateGraph workflow
    utils/                  # Config, logging, API key guard
    tests/                  # pytest test suite
    scripts/                # Seed data script
    main.py                 # FastAPI application entry point
    alembic.ini             # Alembic configuration
  docker/                   # Infrastructure compose file and Docker notes
  scripts/                  # verify.ps1, verify.sh, run_demo.py, validate_compose.py
  docs/
    ARCHITECTURE.md         # Architecture documentation
    DEMO.md                 # End-to-end demo instructions
  docker-compose.yml        # Full stack: frontend, backend, postgres, hindsight
  .env.example
  README.md
```

## Data Notice

All supply chain data in this system is simulated for demonstration purposes.
Supplier names, inventory figures, and purchase order data are fictional examples
clearly labeled as simulated. No real company data is used.

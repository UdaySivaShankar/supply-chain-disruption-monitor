# Docker configuration

This directory holds the Docker configuration that is not tied to a single
service build context.

| File | Purpose |
|---|---|
| `docker-compose.infra.yml` | PostgreSQL and Hindsight only, for native backend/frontend development |

## Where the build files live

| File | Used by |
|---|---|
| `backend/Dockerfile` | `backend` service in the root `docker-compose.yml` (build context `./backend`) |
| `frontend/Dockerfile` | `frontend` service in the root `docker-compose.yml` (build context `./frontend`) |
| `frontend/nginx.conf` | Copied into the frontend image, proxies `/api` to the `backend` service |

Build contexts must contain the files a Dockerfile copies, so the Dockerfiles
stay next to their source instead of in this directory.

## Networking

All services join the `scm_network` bridge network declared in the root
`docker-compose.yml`. On that network the services address each other by name:

- `frontend` calls `http://backend:8000` through the nginx proxy
- `backend` connects to `postgres:5432`
- `backend` connects to `hindsight:8888`

Only the ports required by the operator are published to the host:
`3000` (frontend), `8000` (API), `5432` (PostgreSQL), `8888` (Hindsight memory
API), `9999` (Hindsight Control Plane web UI).

## Hindsight service

Hindsight is pulled from the official Vectorize registry:

| Setting | Value | Why |
|---|---|---|
| Image | `ghcr.io/vectorize-io/hindsight:latest` | The published image. There is no `vectorize/hindsight` repository on Docker Hub. |
| Data volume | `/home/hindsight/.pg0` | The container runs as UID 1000 and keeps its embedded pg0 PostgreSQL there. |
| LLM config | `HINDSIGHT_API_LLM_PROVIDER`, `HINDSIGHT_API_LLM_API_KEY`, `HINDSIGHT_API_LLM_MODEL` | Hindsight needs an LLM for fact extraction; it reuses the `GOOGLE_API_KEY` of the backend by default. |
| Health check | `GET /health` via Python | `/health` is the readiness probe (checks the database). The image ships neither `curl` nor `wget`. |
| `shm_size` | `1g` | Recommended by the Hindsight installation docs for the embedded database. |

Hindsight degrades gracefully: if the container is stopped, the backend logs a
warning and the workflow continues with an empty memory list (see
`backend/hindsight/client.py`).

## Commands

```bash
# Full application stack
docker compose up -d

# Infrastructure only, for native development
docker compose -f docker/docker-compose.infra.yml up -d

# Validate the compose file without starting anything
docker compose config --quiet
```

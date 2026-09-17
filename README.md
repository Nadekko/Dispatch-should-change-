# La Suite interop stack

Local Docker Compose environment that runs [Docs](https://github.com/suitenumerique/docs), [Meet](https://github.com/suitenumerique/meet) and [Dictaphone](https://github.com/suitenumerique/dictaphone) together, with **one copy** of the shared services they all need.

This is a development stack. It is not a production deployment.

## Architecture

Shared once:

| Service | Role |
| --- | --- |
| PostgreSQL 16 | Four databases: `impress`, `meet`, `dictaphone`, `keycloak` |
| Redis 7 | Isolated by DB number (LiveKit, Django/Celery, summary) |
| MinIO (`quay.io/minio/minio`) | One object store, one bucket per app |
| Keycloak 26 | One IdP, three realms (`impress`, `meet`, `dictaphone`) |
| Mailcatcher | Shared outbound mail sink |
| Meet **summary** FastAPI | Transcription/summarization used by both Meet and Dictaphone |

Application services keep their own Django, Celery, and frontend containers.

Interop wiring:

- **Meet → Docs**: after a recording is transcribed, the summary service calls Docs `POST /api/v1.0/documents/create-for-owner/` with `DJANGO_SERVER_TO_SERVER_API_TOKENS`.
- **Dictaphone → summary**: Dictaphone sends transcribe/summarize jobs to the same Meet summary API (`AI_SERVICE_URL`).
- **Dictaphone → Docs**: completed transcripts can be opened/created in Docs with the same server-to-server token, and the generated summary is created as a child document of the transcript document.

```
Dictaphone ──┐
             ├──► summary (Meet) ──► Docs create-for-owner
Meet ────────┘         │
                       └──► WhisperX / LLM (configure in env/summary)
```

MinIO is pulled from **Quay** (`quay.io/minio/minio` and `quay.io/minio/mc`) so the stack does not depend on Docker Hub images that are blocked or license-restricted.

## Prerequisites

- Docker and Docker Compose v2
- GNU Make
- At least 8 GB RAM for the full stack (three Django backends, Next.js, LiveKit, Keycloak)

## Quick start

```shell
make bootstrap
```

That clones Docs, Meet and Dictaphone **as sibling working trees** (not git submodules), applies small local patches, builds images, runs migrations, creates Django superusers, and starts every service. The clones stay untracked so this repo only contains the interop wiring.

Useful follow-ups:

```shell
make ps          # running containers
make logs        # follow logs
make stop        # stop without deleting
make down        # stop and remove containers
make demo        # optional demo content
```

## URLs and credentials

| App | Frontend | API / admin |
| --- | --- | --- |
| Docs | http://localhost:3000 | http://localhost:8071/admin |
| Meet | http://localhost:3001 | http://localhost:8072/admin |
| Dictaphone | http://localhost:3002 | http://localhost:8073/admin |

| What | Username | Password |
| --- | --- | --- |
| Shared Keycloak user (all three apps) | `lasuite` | `lasuite` |
| Docs Keycloak user | `impress` | `impress` |
| Meet Keycloak user | `meet` | `meet` |
| Dictaphone Keycloak user | `dictaphone` | `dictaphone` |
| Django admin (each API) | `admin@example.com` | `admin` |
| Keycloak admin | `admin` | `admin` |
| MinIO console http://localhost:9001 | `lasuite` | `password` |

OIDC is served at http://localhost:8083 (nginx in front of Keycloak). Mailcatcher is at http://localhost:1081.

Dictaphone domain-test users from upstream still work: `user-domain-alpha` / `password-domain-alpha` and `user-domain-beta` / `password-domain-beta`.

Use the shared `lasuite` / `lasuite` account when you want the same email (`lasuite@example.com`) to own documents created from Meet or Dictaphone.

## Redis DB map

One Redis instance, no cross-talk:

| DB | Used by |
| --- | --- |
| 1 | Meet Django / Celery |
| 2 | Docs Django / Celery |
| 3 | Dictaphone Django / Celery |
| 4 | Summary workers |
| 5 | LiveKit + egress |

## MinIO buckets

Created on first boot:

- `impress-media-storage` (versioned)
- `meet-media-storage`
- `dictaphone-media-storage`
- `dictaphone-media-alpha`
- `dictaphone-media-beta`

Each app keeps the access keys it already expects. Only the MinIO root user is shared.

## Transcription / AI

The summary service starts with the stack, but **speech-to-text and LLM calls need an API key**. This stack is pre-wired for [Albert API](https://albert.api.etalab.gouv.fr/swagger).

Copy the example and put the same bearer token in both keys (do not commit this file):

```shell
cp env/summary.local.example env/summary.local
```

Then recreate the summary workers:

```shell
docker compose up -d --force-recreate --no-deps summary summary-transcribe summary-summarize summary-webhook
```

`make bootstrap` also builds Docs email templates (`make docs-mails`). Those files are gitignored in the Docs repo and are required for “open in Docs”.

## Layout

```
compose.yml              # includes the files below
compose.shared.yml       # postgres, redis, minio, keycloak, nginx
compose.docs.yml
compose.meet.yml         # includes LiveKit + summary
compose.dictaphone.yml
env/                     # interop env (no Albert secrets)
env/summary.local        # gitignored Albert API key
patches/                 # applied onto the Meet clone at bootstrap
scripts/                 # CSRF / STT patches + Keycloak realm remap
docker/                  # init scripts, nginx, generated Keycloak realms
docs/ meet/ dictaphone/  # cloned by `make clone`, not committed
```

Server-to-server token shared by Docs, Meet summary, and Dictaphone: `server-api-token` (`DJANGO_SERVER_TO_SERVER_API_TOKENS` / `DOCS_SERVER_TO_SERVER_API_KEY` / `LASUITE_DOCS_SERVER_TO_SERVER_API_KEY`).

## Ports

| Port | Service |
| --- | --- |
| 3000 | Docs (nginx proxy → frontend + `/api`) |
| 3001 | Meet frontend |
| 3002 | Dictaphone frontend |
| 4000 | Docspec |
| 4444 | Docs y-provider (collaboration websocket) |
| 8071 | Docs Django |
| 8072 | Meet Django |
| 8073 | Dictaphone Django |
| 8001 | Summary API |
| 8080 | Keycloak (direct) |
| 8083 | Keycloak via nginx + Docs media auth |
| 9000 / 9001 | MinIO S3 / console |
| 15432 | PostgreSQL |
| 7880–7882, 3478, 30000–30100 | LiveKit |

## Notes

- Dictaphone containers remap `localhost` to the Docker host so `DOCS_BASE_URL=http://localhost:3000` works both for the create-for-owner API and for “open in Docs” links in the browser.
- Local patches (CSRF origins for ports 3001/3002, Albert ogg→wav transcode) live in `scripts/patch_upstreams.py` and `patches/`. They are reapplied by `make clone`.
- Keycloak realm JSON files from upstream share UUIDs. `scripts/prepare_realms.py` remaps them so all three realms can be imported into one Keycloak.
- Pulling MinIO from Quay avoids Docker Hub license/availability issues with `minio/minio`.

# Heartbeat

A monorepo containing a wiki application with multi-role RBAC, infrastructure-as-code, and supporting tools.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI, SQLAlchemy (async), Pydantic |
| Frontend | Next.js 16, React 19, TypeScript 5, Mantine UI, Tailwind CSS 4 |
| Database | SQLite (default) / PostgreSQL |
| Auth | JWT (python-jose), OAuth2 |
| Testing | pytest, pytest-asyncio |
| Infra | Terraform (Azure), Kubernetes, Docker |
| Dev Env | Nix, direnv |

## Project Structure

```
heartbeat/
├── app/wiki/                 # Main wiki application
│   ├── backend/              # FastAPI backend (see .claude/docs/wiki_app.md)
│   └── frontend/             # Next.js frontend
├── terraform/                # Azure infrastructure (AKS, VMs, ACR)
├── k8s/manifests/            # Kubernetes deployment configs
├── website/                  # Secondary apps (ghost, bookstack, quiz)
├── youtube/                  # YouTube subtitle downloader tool
└── bin/                      # Development/deployment scripts
```

## Essential Commands

### Wiki Backend

```bash
cd app/wiki/backend
uv sync                       # Install dependencies
uv run uvicorn app.main:app --reload  # Start dev server (port 8000)
uv run pytest                 # Run tests
```

### Wiki Frontend

```bash
cd app/wiki/frontend
yarn install                  # Install dependencies
yarn dev                      # Start dev server (port 3000)
yarn build                    # Production build
yarn lint                     # Run ESLint
```

### Development Environment

```bash
nix-shell                     # Enter Nix shell (auto-activates via direnv)
```

### Infrastructure

```bash
cd terraform/<component>
terraform init && terraform plan
```

## Key Entry Points

| Purpose | File |
|---------|------|
| Backend main | `app/wiki/backend/app/main.py:1` |
| API routes | `app/wiki/backend/app/api/` |
| Database models | `app/wiki/backend/app/models.py:1` |
| Auth logic | `app/wiki/backend/app/auth.py:1` |
| RBAC services | `app/wiki/backend/app/services.py:1` |
| Frontend layout | `app/wiki/frontend/src/app/wiki-layout.tsx:1` |
| Page editor | `app/wiki/frontend/src/app/page/[id]/page.tsx:1` |

## Database Schema (Core)

- **User** - Email auth, password_hash, multi-role support
- **Role** - System roles (superadmin, admin, member, public) + custom roles
- **UserRole** - Many-to-many junction table
- **Page** - Content with hierarchy, soft deletes
- **Folder** - Hierarchical organization, public/private
- **Permission** - RBAC permission model (subject/object/level)
- **Setting** - Key-value configuration store

## API Endpoints

| Route | Purpose |
|-------|---------|
| `/token` | OAuth2 authentication |
| `/me` | Current user info |
| `/admin/*` | User/role administration |
| `/folders/*` | Folder CRUD |
| `/pages/*` | Page CRUD |
| `/roles/*` | Role management |
| `/settings/*` | Settings management |
| `/export` | Data export to ZIP |

## Configuration

- Backend config via environment variables or `.env` file: `app/wiki/backend/app/db.py:10-20`
- Key settings: `DATABASE_URL`, `SECRET_KEY`, OAuth credentials
- Runtime settings stored in database `Setting` table

## Testing

Backend tests use in-memory SQLite with fixtures for async operations:
- Test config: `app/wiki/backend/tests/conftest.py:1`
- RBAC tests: `app/wiki/backend/tests/test_rbac.py:1`
- CRUD tests: `app/wiki/backend/tests/test_crud.py:1`

Run tests: `cd app/wiki/backend && uv run pytest -v`

## Additional Documentation

| Topic | File |
|-------|------|
| Wiki app details | `.claude/docs/wiki_app.md` |

## Recent Development

Currently in **Phase 11**: Multi-role RBAC implementation. Recent commits focus on:
- Multi-role user assignment UI
- Role management API
- Unit tests for RBAC system
- Database schema updates for multi-role support

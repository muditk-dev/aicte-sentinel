# AICTE Sentinel — Statutory Regulatory Approval & Compliance Intelligence Platform

> **SIH 2026 Problem Statement ID:** 26262  
> **Target Jurisdiction:** All India Council for Technical Education (AICTE), Ministry of Education, Government of India  
> **Statutory Basis:** AICTE Approval Process Handbook (APH 2026-27)

---

## 1. Overview & Statutory Mission

**AICTE Sentinel** is a secure, role-based, end-to-end regulatory platform designed to govern technical education institutions across India. It modernizes the statutory lifecycle of approvals, scrutinies, and compliance monitoring with high-assurance auditability.

### Strict Statutory Guardrail Principle
> **Statutory Determination Boundary:** Machine learning models and automated algorithms provide informational advisory assistance only (e.g. delay risk indicators and APH clause citations). **AI NEVER makes statutory approval decisions, never mutates workflow states automatically, and never verifies legal compliance without authorized human action.**

---

## 2. Technology Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, TanStack Query v5, React Router v6.
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (Async), Pydantic v2, Alembic.
- **Security:** Argon2id password hashing, JWT Bearer tokens, Role-Based Access Control (RBAC), PostgreSQL Row-Level Security (RLS) tenant isolation context.
- **Audit & Cryptography:** SHA-256 continuous hash-chained ledger and Merkle root verification.
- **Databases & Storage:** PostgreSQL 16 with `pgvector`, Redis 7, MinIO S3-compatible document vault, and zero-config local SQLite fallback for standalone development.

---

## 3. Project Structure

```
.
├── backend/
│   ├── alembic/              # Alembic migration scripts and environment
│   ├── app/
│   │   ├── api/              # Versioned REST endpoints (/api/v1/*, /api/health, /api/ready)
│   │   ├── audit/            # Cryptographic SHA-256 hash chaining & verification
│   │   ├── core/             # Configuration, async DB session, logging, exceptions
│   │   ├── models/           # SQLAlchemy 2.x declarative domain entities
│   │   ├── schemas/          # Pydantic v2 validation models
│   │   ├── security/         # Argon2id, JWT tokens, RLS tenant context, auth dependencies
│   │   ├── workers/          # Background scheduler for SLA monitoring
│   │   └── workflows/        # Guarded Finite State Machine (FSM) engine
│   ├── tests/                # Automated pytest suite (in-memory async DB)
│   ├── alembic.ini           # Migration settings
│   ├── Dockerfile            # Container definition
│   └── requirements.txt      # Pinned dependencies
├── frontend/
│   ├── src/
│   │   ├── components/       # Enterprise UI components (Header, Sidebar, Badges, Modals)
│   │   ├── layouts/          # Authenticated layout shell
│   │   ├── lib/              # API fetch client and date formatters
│   │   ├── pages/            # Dashboard, Applications, Detail, Institutions, Workflows, Audit
│   │   ├── routes/           # React Router with ProtectedRoute
│   │   ├── services/         # Typed API consumption services
│   │   └── types/            # TypeScript interfaces
│   ├── Dockerfile            # Container definition
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite configuration & API proxy
├── docs/
│   ├── ARCHITECTURE.md       # Complete system architecture and security model
│   └── IMPLEMENTATION_PLAN.md# 16-module master roadmap and status matrix
├── scripts/
│   └── seed_data.py          # Deterministic synthetic seed data generator
├── docker-compose.yml        # Orchestration (Postgres+pgvector, Redis, MinIO, ClamAV)
├── .env.example              # Documented environment configuration template
└── pytest.ini                # Pytest configuration
```

---

## 4. Quickstart Guide (Local Development)

### 4.1 Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 4.2 Backend Setup & Synthetic Seed Data
```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Seed deterministic demo data (users, institutions, workflows, applications, audit chain)
python scripts/seed_data.py

# 4. Run the FastAPI development server
python -m uvicorn app.main:app --app-dir backend --reload --port 8000
```
*The API is now running at `http://127.0.0.1:8000`. OpenAPI documentation is available at `http://127.0.0.1:8000/api/docs`.*

### 4.3 Frontend Setup & Execution
```powershell
# In a separate terminal:
cd frontend
npm install
npm run dev
```
*The frontend dashboard is accessible at `http://localhost:5173`.*

---

## 5. Synthetic Demo Personas & Credentials

The seed command initializes deterministic test accounts across every statutory role with Argon2id password hashing:

| Statutory Role | Official Email | Demo Password | Institutional Scope |
|:---|:---|:---|:---|
| **Central Super Admin** | `superadmin@aicte-india.org` | `Sentinel@Admin2026!` | National Jurisdiction |
| **Regional Officer** | `ro.delhi@aicte-india.org` | `Regional@2026!` | Northern Region Docket |
| **Scrutiny Officer** | `scrutiny.lead@aicte-india.org` | `Scrutiny@2026!` | Document Verification Desk |
| **EVC Expert Committee**| `evc.prof@iitd.ac.in` | `Expert@2026!` | Inspection Panels |
| **College Signatory** | `director@ditm-delhi.edu.in` | `College@2026!` | Delhi Inst. of Tech & Mgmt |

*Note: The login page features one-click buttons to easily populate any of these demo credentials.*

---

## 6. Automated Testing & Build Validation

### 6.1 Backend Test Suite (Pytest)
Executes 10 comprehensive unit and integration tests against an isolated in-memory SQLite database, verifying auth tokens, tenant RLS isolation, guarded state machine transitions, and cryptographic audit hash validation:
```powershell
.\.venv\Scripts\pytest -v backend/tests
```
**Outcome:** `10 passed in ~7s`

### 6.2 Frontend Production Build (TypeScript + Vite)
```powershell
cd frontend
npm run build
```
**Outcome:** `Built in ~6s (0 TypeScript errors, production assets emitted in dist/)`

---

## 7. Key Diagnostic & Verification Endpoints

- **Liveness Probe:** `GET /api/health` — Confirms process availability and uptime.
- **Readiness Probe:** `GET /api/ready` — Checks database connectivity and active dialect.
- **Cryptographic Audit Verifier:** `GET /api/v1/audit/verify` — Traverses the entire SHA-256 event chain from Genesis and validates that zero database modifications or deletions have occurred.
- **OpenAPI Schema:** `GET /api/docs` or `GET /api/openapi.json`.

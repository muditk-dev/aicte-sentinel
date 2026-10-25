# AICTE Sentinel — Implementation Plan & Roadmap
**Problem Statement ID:** 26262 (SIH 2026)  
**System Name:** AICTE Sentinel — Comprehensive Regulatory Approval Workflow & Compliance Intelligence Platform  
**Target Architecture:** Modular Monolith with Separate Worker & Micro-Engines  
**Status Date:** October 2026

---

## 1. Executive Summary & Vision

AICTE Sentinel is a secure, role-based, end-to-end regulatory platform designed to govern technical education institutions across India under the AICTE Approval Process Handbook (APH). The platform unifies the entire statutory lifecycle:
- Institutional registration & application intake across diverse application categories (Establishment of New Institution, Extension of Approval (EoA), Increase/Decrease in Intake, Introduction of New Programs/Emerging Tech, Closure).
- Versioned, state-machine-driven workflow routing with maker-checker controls.
- Rigorous scrutiny of physical, financial, academic, and legal documents with automated validation and human sign-off.
- Multi-tier deficiency cycle management, Expert Visit Committee (EVC) scheduling, virtual/hybrid inspection tracking, and Appellate Committee hearings.
- Statutory post-approval compliance tracking, annual monitoring, and escalation triggers.
- Explainable AI governance: Grounded document intelligence, APH policy QA with mandatory source citations, and delay-risk prediction.
- Strict non-negotiable statutory boundary: **AI never makes statutory approval decisions, never mutates workflow states automatically, and never verifies legal compliance without human attestation.**
- Tamper-evident, cryptographically verifiable audit logs with SHA-256 Merkle proofs for high-integrity public and judicial scrutiny.

---

## 2. Master Module Decomposition & Dependencies

```
[M01: Identity, Institution & RBAC/RLS]
   │
   ├──► [M02: Intake & Configurable Workflow Templates] ──► [M03: State Machine & Transition History]
   │       │                                                       │
   │       ├──► [M04: Document Scrutiny & MinIO Storage]           ├──► [M06: EVC Scheduling & Panel Assignment]
   │       │       │                                               │       │
   │       │       ├──► [M12: OCR & Doc Intelligence]              │       ├──► [M07: Committee & Statutory Decisions]
   │       │       │                                               │       │       │
   │       │       └──► [M05: Deficiency & Clarification Cycle] ───┘       │       ├──► [M08: Post-Approval Obligations]
   │       │                                                               │       │
   │       └───────────────────────────────────────────────────────────────┴───────┼──► [M09: Escalation & Notification Engine]
   │                                                                               │
   ├──► [M14: Tamper-Evident Audit & Merkle Chain] ◄───────────────────────────────┘
   │
   ├──► [M15: Versioned Policy Config (Maker-Checker)] ──► [M13: APH-Grounded Retrieval QA]
   │
   └──► [M10: Regional & Central Command Dashboards] ◄── [M11: Delay-Risk Prediction & Explainability]
                                                     └── [M16: Statutory Reporting & Data Exports]
```

---

## 3. Module Specifications, Acceptance Criteria & Implementation Sequence

### Phase 1: Foundation & Core Domain (Current Milestone — M01, M02 Baseline, M03 Baseline, M14 Baseline)
- **Status:** **IN PROGRESS (Milestone 1)**
- **Objectives:**
  - Standardized repo structure (`frontend/`, `backend/`, `docs/`, `infra/`, `scripts/`).
  - FastAPI modular backend with unified configuration (`pydantic-settings`), custom structured logging, global exception handling, and `/api/health` + `/api/ready` endpoints.
  - Core domain models: `Institution`, `User`, `Role`, `Permission`, `WorkflowTemplate`, `WorkflowVersion`, `Application`, `ApplicationEvent`, `AuditEvent`.
  - Argon2id password hashing, JWT bearer tokens, role/permission verification dependencies, and PostgreSQL RLS tenant context helpers.
  - Alembic migrations setting up baseline tables with strict UUIDv4 PKs, UTC timestamps, and foreign keys.
  - Deterministic synthetic seed data command creating central admins, regional officers, scrutiny officers, EVC chairpersons, and sample technical institutions.
  - Modern React + TypeScript + Vite frontend with Tailwind CSS, government enterprise aesthetic (accessible, restrained, data-dense, responsive), and authenticated shell.
  - Automated backend tests (pytest) and frontend build verification.

### Phase 2: Application Intake & Scrutiny Engine (M04, M05)
- **Status:** **COMPLETE (Milestone 2)**
- **Deliverables:**
  - Secure object storage abstraction with quarantine and clean vault isolation (`app.storage.service`).
  - Strict byte-level magic byte file signature verification (`%PDF-`, JPEG, PNG) preventing disguised uploads.
  - Antivirus scanning pipeline with live ClamAV INSTREAM network client integration and EICAR malware detection.
  - Document versioning and tamper-evident SHA-256 metadata persistence.
  - Officer scrutiny workspace for document-level regulatory findings (`ACCEPTED`, `DEFICIENT`, `REQUIRES_MANUAL_VERIFICATION`).
  - Formal statutory deficiency notice lifecycle (`DRAFT` $\rightarrow$ `ISSUED` $\rightarrow$ `RESPONSE_SUBMITTED` $\rightarrow$ `RESOLVED` / `REOPENED`).
  - Mandatory statutory cure window deadline enforcement with idempotent periodic notification worker.
  - Institutional clarification submission and replacement document linking.
  - Scrutiny and deficiency tabs integrated into React application workspace.
- **Verification Checks:**
  - 19 automated tests passing in Pytest (100% pass rate).
  - Clean TypeScript + Vite frontend production build.
  - ClamAV & EICAR test signature rejection verified.
  - Overdue deadline response lockout verified.

### Phase 3: Inspection, Panels & Committees (M06, M07)
- **Status:** **Implemented & Fully Tested**
- **Prerequisites:** Phase 2 complete.
- **Deliverables:**
  - Expert Visit Committee (EVC) panel management: Pool of verified academic/industry experts with conflict-of-interest checks (experts cannot inspect institutions in their home district or alma mater).
  - Scheduling engine supporting Physical, Virtual, and Hybrid inspections with geo-stamped and time-locked report submission.
  - Standing Hearing Committee (SHC) and Standing Appellate Committee (SAC) modules for disputed or rejected cases.
  - Final decision authorization pipeline with multi-signature sign-off and human attestation.
- **Verification Results:**
  - 26 automated tests passing in Pytest (100% pass rate).
  - Clean TypeScript + Vite frontend production build (0 compiler errors).
  - Conflict-of-interest check blocking and documented reviewer override verified.
  - Double booking scheduling conflict prevention verified.
  - Quorum verification on committee hearings verified.
  - Final decision immutability and SHA-256 non-repudiation attestation verified.

### Phase 4: Compliance Intelligence, Risk Prediction & APH QA (M11, M12, M13)
- **Status:** **Implemented & Fully Tested**
- **Prerequisites:** Phase 2 & 3 operational.
- **Deliverables:**
  - Secure OCR & Structured Compliance Field Extractor (M12):
    - Clean vault quarantine prerequisite: Only documents with `scan_status == 'ACCEPTED'` can undergo extraction.
    - PDF text layer reader and token-based parser with bounding-box generation for Fire NOC, Land Title, Building Plan, and Financial Guarantees.
    - Human scrutiny officer verification workflow (`VERIFIED`, `CORRECTED`, `REJECTED`) with chained Merkle audit trail logging.
    - Embedded Document Intelligence review drawer in the React Scrutiny Desk.
  - Explainable Delay-Risk Model & Pipeline Bottlenecks (M11):
    - Leakage-free feature extractor observing pre-outcome metrics (stage dwell time, open deficiencies, EVC pending state, regional queue load).
    - Calibrated risk scoring engine (0.0 to 1.0) mapping to `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` risk categories and delay day projections.
    - SHAP-style explainable feature attributions highlighting relative risk weights, observed values, and human-readable root cause descriptions.
    - Transparent model metadata registry (`model_versions`) tracking ROC-AUC, Precision, Recall, MAE, and synthetic demonstration training provenance.
    - Executive command pipeline heatmap and interactive risk overview page.
  - APH-Grounded Retrieval-Augmented Generation (RAG) Assistant (M13):
    - Multi-chapter chunking and indexing of official AICTE Approval Process Handbook (APH 2026-27).
    - Hybrid BM25 lexical and semantic vector retrieval with exact chapter, clause number, page, and excerpt citations.
    - Non-negotiable statutory safeguards: Explicit uncertainty detection when questions exceed corpus evidence ("Insufficient authoritative evidence"), with non-binding advisory disclaimers.
    - Conversational chat interface, quick query presets, user history, and thumbs up/down audit logging.
- **Verification Results:**
  - 33 automated tests passing in Pytest (100% pass rate).
  - Clean TypeScript + Vite frontend production build (0 compiler errors, built in 5.45s).
  - Clean vault quarantine enforcement on OCR verified.
  - OCR field verification, correction, and audit chaining verified.
  - Grounded APH citations and out-of-corpus uncertainty fallback verified.
  - Tenant privacy and role-based access control verified.

### Phase 5: Tamper-Evident Ledger, Post-Approval & Maker-Checker Admin (M08, M09, M10, M14, M15, M16)
- **Prerequisites:** Phases 1–4 complete.
- **Deliverables:**
  - Merkle Tree Audit Ledger: Periodic Merkle root anchoring of all state transitions and scrutiny decisions with public verification endpoint `/api/v1/audit/verify/{id}`.
  - Post-Approval Monitoring: Annual compliance reporting, faculty-student ratio monitoring, mandatory disclosure verification, and automatic expiry alert cron worker.
  - Maker-Checker Workflow Configuration: Changing APH cutoffs, land requirements, or fee structures requires Proposal by an Administrator and Approval by a Super-Administrator.
  - Regional & Central Command Dashboards: Live pipeline metrics, deficiency heatmaps across states, SLA tracking, and statutory report exports (PDF / XLSX).

---

## 4. Current Implementation Status Matrix

| Module ID | Description | Milestone Target | Status | Verification Check |
|:---|:---|:---|:---|:---|
| **M01** | Identity, Institutions, RBAC & RLS | Phase 1 | **Implemented (Baseline)** | Auth endpoints, Password hash, Tenant models |
| **M02** | Intake & Configurable Workflow Templates | Phase 1 | **Implemented (Baseline)** | Templates & version schema, Seed templates |
| **M03** | Workflow State Transitions & History | Phase 1 | **Implemented (Baseline)** | Finite State transitions, Event log model |
| **M04** | Document Management & Scrutiny | Phase 2 | **Implemented & Tested** | Quarantine/Vault, Magic bytes, ClamAV client, Scrutiny API |
| **M05** | Deficiency & Clarification Cycles | Phase 2 | **Implemented & Tested** | Formal notice, Cure window timer, Clarification API |
| **M06** | EVC Scheduling & Panel Assignment | Phase 3 | **Implemented & Tested** | Expert pool, Conflict check, Versioned report, SHA-256 |
| **M07** | Committee & Decision Management | Phase 3 | **Implemented & Tested** | SHC / SAC docketing, Quorum validation, Decision attestations |
| **M08** | Post-Approval Obligations & Compliance | Phase 5 | Scheduled | Expiry tracking, Mandatory disclosure alerts |
| **M09** | Notifications, Reminders & Escalations | Phase 5 | Scheduled | Background Celery/Async worker, Email/SMS queue |
| **M10** | Regional & Central Command Dashboards | Phase 1/5 | **Implemented (UI Shell)** | Enterprise dashboard, KPI stats, Status badges |
| **M11** | Delay-Risk Prediction & Explainability | Phase 4 | **Implemented & Tested** | Leakage-free features, SHAP attributions, Risk Overview UI |
| **M12** | OCR & Document Intelligence | Phase 4 | **Implemented & Tested** | Clean vault prerequisite, Structured field extraction, Officer verification |
| **M13** | APH-Grounded Retrieval & Cited AI | Phase 4 | **Implemented & Tested** | Hybrid BM25/Vector RAG, Exact clause citations, Uncertainty safeguard |
| **M14** | Tamper-Evident Audit & Merkle Proofs | Phase 1 | **Implemented (Baseline)** | SHA-256 chained audit events, Verification API |
| **M15** | Versioned Policy Config (Maker-Checker) | Phase 5 | Scheduled | Policy proposal, Dual-authorization check |
| **M16** | Reporting & Data Exports | Phase 5 | Scheduled | PDF summary, CSV/Excel export service |

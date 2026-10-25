# AICTE Sentinel — Architecture Specification

## 1. System Overview & Boundaries

AICTE Sentinel is designed to replace fragmented, manual approval workflows with an auditable, high-assurance digital operating system for AICTE regulatory oversight.

```
                           ┌─────────────────────────────────────────────────────────┐
                           │                     CLIENT BROWSERS                     │
                           │     Institution Admins  •  Scrutiny Officers            │
                           │     Regional Directors  •  EVC Experts  •  Public       │
                           └────────────────────────────┬────────────────────────────┘
                                                        │ HTTPS (TLS 1.3)
                                                        ▼
                           ┌─────────────────────────────────────────────────────────┐
                           │               EDGE REVERSE PROXY / NGINX                │
                           │    - Static Frontend Assets (Vite React SPA)            │
                           │    - API Rate Limiting & TLS Termination                │
                           └──────────────┬───────────────────────────┬──────────────┘
                                          │                           │
                   Static / UI Routes     │                           │ /api/v1/*
                                          ▼                           ▼
                           ┌────────────────────────┐  ┌─────────────────────────────┐
                           │   REACT 19+ TS SPA     │  │      FASTAPI REST CORE      │
                           │ Tailwind + Radix UI    │  │ - Pydantic Request Validation│
                           │ TanStack Query + State │  │ - Dependency Injection Auth │
                           └────────────────────────┘  │ - State Machine Engine      │
                                                       │ - Row-Level Security Enforce│
                                                       └──────────────┬──────────────┘
                                                                      │
                      ┌───────────────────────┬───────────────────────┼────────────────────────┐
                      │                       │                       │                        │
                      ▼                       ▼                       ▼                        ▼
       ┌────────────────────────┐ ┌──────────────────────┐ ┌────────────────────┐ ┌─────────────────────┐
       │   POSTGRESQL 16+ RDBMS │ │     REDIS 7+ CACHE   │ │  MINIO / S3 BLOB   │ │  BACKGROUND WORKER  │
       │ - Relational Workflows │ │ - Session blacklist  │ │ - Upload Quarant.  │ │ - SLA Escalations   │
       │ - Multi-tenant RLS     │ │ - Rate limit counters│ │ - Clean Doc Vault  │ │ - ClamAV Antivirus  │
       │ - pgvector Embeddings  │ │ - Worker Queue       │ │ - SHA-256 Hashing  │ │ - Merkle Anchoring  │
       │ - Immutable Audit Log  │ └──────────────────────┘ └────────────────────┘ └─────────────────────┘
       └────────────────────────┘
```

---

## 2. Core Security Model

### 2.1 Identity, Authentication & Session Security
1. **Password Storage:** Uses **Argon2id** (`t=3, m=65536, p=4`) adhering to OWASP recommendations. Passwords are never logged or stored in plaintext.
2. **Token Lifecycle:** Short-lived JWT Access Tokens (15–30 minutes) combined with strictly scoped refresh tokens. Privileged roles (Regional Officers, Central Council) require TOTP MFA.
3. **Account Lockout & Throttling:** Progressive delay and account lockout after 5 consecutive failed attempts within a 15-minute sliding window.

### 2.2 PostgreSQL Row-Level Security (RLS) & Multi-Tenancy
- Technical institutions operate within a strict tenant boundary (`institution_id`).
- When a request is authenticated, the backend session sets the active tenant context:
  ```sql
  SET LOCAL app.current_tenant = :tenant_id;
  SET LOCAL app.current_user_id = :user_id;
  SET LOCAL app.current_role = :role;
  ```
- RLS policies ensure that institution representatives can ONLY view and mutate their own institution's applications, documents, and deficiency notices.
- AICTE administrative officers (Central, Regional, Scrutiny) possess verified supervisory roles that bypass tenant restrictions strictly through audited administrative queries.

### 2.3 Strict Separation: AI Assistance vs. Statutory Authority
- **Statutory Decision Isolation:** No machine learning model, vector similarity score, or automated algorithm has database write permissions on `applications.status` or `committee_decisions`.
- **Advisory Only:** All AI inference (delay risk indicators, OCR extracted fields, APH policy references) is explicitly marked in the database and UI with `is_automated_advisory: true`, requiring active human affirmation before any record becomes legally binding.

### 2.4 Document Security & Antivirus Quarantine
- Direct public uploads are prohibited.
- Files are staged in a **Quarantine Bucket** where the ClamAV daemon inspects the payload.
- File integrity: Client-supplied MIME headers are untrusted; magic-byte inspection verifies file signatures (PDF, PNG, JPG).
- Files verified as clean are transferred to the **Encrypted Vault** and tagged with their immutable SHA-256 checksum.

---

## 3. Data Flows & Statutory State Machine

### 3.1 Statutory Application Flow
```
[DRAFT]
   │  (Institution submits)
   ▼
[SUBMITTED / PAYMENT_PENDING]
   │  (Payment verified)
   ▼
[UNDER_SCRUTINY] ◄────────────────────────────────────────┐
   │                                                      │
   ├──► [DEFICIENCY_ISSUED] ──► [RESUBMITTED_BY_INST] ────┘
   │
   │  (Scrutiny Passed)
   ▼
[EVC_SCHEDULED]
   │
   ▼
[EVC_CONDUCTED]
   │
   ├──► [RECOMMENDED_APPROVAL] ────────► [AUTHORIZED_DECISION: APPROVED / CONDITIONAL]
   │                                           ▲
   └──► [STANDING_HEARING]                     │
              │                                │
              ├──► [RECOMMENDED_APPROVAL] ─────┘
              │
              └──► [REJECTED] ──► [APPELLATE_REVIEW] ──► [SAC_DETERMINATION]
```

### 3.2 EVC Panel Allocation & Conflict-of-Interest Verification Engine
1. **Multi-Vector Conflict Assessment:**
   - **Direct Institution Affiliation:** Match against expert's declared current or prior appointments.
   - **Mandatory Geographic Independence:** Match between expert's declared residential/working district and the target institution's district within the same state.
   - **Alma Mater Independence:** Match against institution name or code matching expert's degree-granting alma mater.
   - **Explicit Ethical Declarations:** Free-text and structured declarations on record.
2. **Reviewer Exemption Workflow:**
   - When a statutory conflict is flagged, assignment is blocked automatically.
   - Regional Officers may only override when permitted by policy, requiring a mandatory documented justification recorded in the immutable audit trail.
3. **Report Integrity & Non-Repudiation:**
   - Inspection reports are versioned. Each submission computes a canonical SHA-256 payload digest.
   - Subsequent changes require formal review and new version increment.

### 3.3 Quorum-Governed Committee Adjudication & Decision Attestation
1. **Standing Benches:**
   - Standing Hearing Committees (SHC) and Standing Appellate Committees (SAC) enforce configurable statutory quorum before minutes and advisory recommendations can be recorded.
2. **Authorized Final Decisions:**
   - Consequential regulatory outcomes (`APPROVED`, `CONDITIONALLY_APPROVED`, `REJECTED`) require an authorized human officer with verified authority level.
   - Immutability: Once issued, decisions cannot be edited; only formally reconsidered through an auditable SAC appellate petition.
   - Non-repudiation: Computes a SHA-256 attestation digest over the decision payload and human oath text.

Every transition requires:
1. An authenticated actor with matching `Permission`.
2. Transition guards (e.g. Scrutiny can only be approved if 0 unresolved critical deficiencies remain).
3. Automatic creation of an immutable `ApplicationEvent` and `AuditEvent`.

---

## 4. Tamper-Evident Audit Model (Merkle Anchor)

1. **Chained Events:** Each `AuditEvent` record computes a SHA-256 hash chaining:
   $$\text{Hash}_n = \text{SHA256}(\text{Hash}_{n-1} \,\|\, \text{Timestamp} \,\|\, \text{ActorID} \,\|\, \text{Action} \,\|\, \text{PayloadHash})$$
2. **Batch Merkle Tree:** Every 24 hours (or upon major statutory milestone), the background worker calculates the Merkle Root of all daily events and persists it in a tamper-evident root table with external anchoring capability.
3. **Public Verifier:** A public endpoint allows citizens, institutions, or courts to input an Application Reference Number and verify the exact cryptographic lineage of every approval decision.

---

## 5. Deployment Topology & Container Architecture

- **Docker Compose:** Provides deterministic local development orchestration:
  - `web`: Vite React SPA server / Nginx container.
  - `api`: FastAPI backend running Uvicorn workers.
  - `worker`: Python background process for cron, SLA monitoring, and event processing.
  - `db`: PostgreSQL 16 with `pgvector` extension enabled.
  - `redis`: Redis 7 Alpine for broker and caching.
  - `storage`: MinIO S3-compatible object store.
  - `clamav`: ClamAV daemon for file scanning.
- **Environment Management:** Driven strictly by `.env` adhering to 12-factor application methodology.

---

## 6. Compliance Intelligence, OCR & Grounded APH Assistant (Phase 4)

```
                            ┌────────────────────────────────────────────────────────┐
                            │               AICTE COMPLIANCE INTELLIGENCE            │
                            └───────────────────────────┬────────────────────────────┘
                                                        │
                      ┌─────────────────────────────────┼────────────────────────────────┐
                      ▼                                 ▼                                ▼
       ┌─────────────────────────────┐   ┌─────────────────────────────┐  ┌─────────────────────────────┐
       │   M11: DELAY-RISK PREDICTION│   │     M12: DOCUMENT OCR       │  │   M13: GROUNDED APH RAG     │
       │ - Leakage-Free Features     │   │ - Clean Vault Prerequisite  │  │ - Official APH 2026-27      │
       │ - Pre-Outcome Observations  │   │ - PDF & Token Stream Parser │  │ - BM25 & Semantic Hybrid    │
       │ - SHAP Attribution Weights  │   │ - Bounding Box & Confidence │  │ - Chapter/Clause Citations  │
       │ - Calibrated Risk Scores    │   │ - Scrutiny Officer Verify   │  │ - Uncertainty Fallback      │
       │ - Model Versioning Metadata │   │ - Merkle Audit Chained      │  │ - Non-Binding Advisory Label│
       └─────────────────────────────┘   └─────────────────────────────┘  └─────────────────────────────┘
```

### 6.1 M11: Explainable Delay-Risk Prediction
1. **Leakage-Free Feature Engineering:** Only uses historical observations available at prediction time (stage dwell time, unresolved deficiencies count, document defect rates, EVC inspection status, and regional backlog density).
2. **Explainable SHAP-Style Attributions:** Each prediction generates decomposed feature impacts (`INCREASES_RISK` / `REDUCES_RISK`) with relative weights and human-readable descriptions for regional coordinators.
3. **Model Versioning:** Tracked in `model_versions` table with metrics (ROC-AUC, Precision, Recall, MAE) and synthetic baseline calibration metadata.
4. **Statutory Guardrail:** Flagged `is_automated_advisory: True`. Predictive outputs cannot trigger transitions or statutory outcomes.

### 6.2 M12: Secure Document OCR & Structured Extraction
1. **Clean Vault Quarantine Prerequisite:** Any document whose `scan_status != 'ACCEPTED'` is strictly rejected with `DOCUMENT_NOT_CLEAN` status 400.
2. **Structured Field Extractors:** Parses Fire NOC validity dates, Land Deed registration numbers and acreages, and Building Plan plinth areas with confidence scoring and page coordinate bounding boxes.
3. **Scrutiny Officer Review Lifecycle:** AI-extracted fields are stored as `PENDING` until an authorized Scrutiny Officer performs `VERIFIED`, `CORRECTED` (with justification), or `REJECTED`, recording an immutable chained audit event.

### 6.3 M13: APH-Grounded Retrieval-Augmented Generation (RAG)
1. **Authoritative Corpus:** Indexed AICTE Approval Process Handbook (APH 2026-27) divided into chapters, clauses, and norm categories.
2. **Hybrid Lexical & Semantic Retrieval:** Combines BM25 scoring with vector similarity, ensuring zero external vendor lock-in.
3. **Mandatory Citations & Uncertainty Safeguard:** Every answer includes exact chapter, clause, page, and excerpt citations. If query exceeds indexed corpus coverage, the assistant emits an explicit uncertainty warning rather than hallucinating regulatory rules.

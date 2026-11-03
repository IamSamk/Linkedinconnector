# LinkedIn Public Intelligence & Cohort Discovery Suite (2026 Hardened Edition)

A full-stack OSINT & career intelligence platform built with **Next.js 16.4.1** (`pnpm 12.17.0`) and **FastAPI 0.162.0** (`uvicorn 0.54.0`), hardened against the **Black October (October 2026)** supply-chain and framework vulnerabilities.

---

## 🛡️ Post-"Black October" (Oct 2026) Security Hardening

This project is explicitly configured to mitigate the major October 2026 disclosures:

1. **Next.js Out-of-Band RCE Patches (`CVE-2026-96889`, `GHSA-673q-mjm6-r5xr`, `GHSA-p3m5-59mp-jv5r`):**
   - Pinned to **`next@16.4.1`** and **`react@19.2.6`** (fixing the `use cache` multi-typed-array RSC RCE and Server Actions DoS).
   - Forced **`sharp >= 0.35.5`** via `pnpm.overrides` in `package.json` to ensure `librsvg >= 2.63.2` is used, eliminating the `CVE-2026-96889` heap/use-after-free RCE.
   - Explicitly enforced `images: { dangerouslyAllowSVG: false }` and strict Content-Security-Policy headers in `next.config.ts`.
   - Includes `pnpm run security:verify` (`scripts/check-october-cves.mjs`) to audit installed lockfile versions before build.
2. **PyPI & npm Supply-Chain Protections (Post-LiteLLM `1.107.0` Incident - Oct 21, 2026):**
   - Zero dependency on compromised LLM proxy wrappers (`litellm` is strictly excluded; local Ollama or Serper calls use direct `httpx` clients with pinned `certifi` CA bundles following the Oct 2026 eMudhra CA incident).
   - `.npmrc` enforces `ignore-scripts=true` to block malicious postinstall hooks during `pnpm install`.
3. ** ASGI & Runtime Stack:**
   - **FastAPI `0.162.0`** + **Uvicorn `0.54.0`** running on Python 3.12/3.13 without `--reload` sub-process event-loop conflicts on Windows 11.

---

## 🚀 Core Capabilities

1. **Workflow 1: Bulk CSV -> Structured "LinkedIn CV" Pipeline**
   - Upload a CSV of names (`name`, `organization`, `location`, `batch`).
   - **Stage A (Zero Account Risk):** Resolves exact `/in/{slug}` URLs via Serper.dev Google SERP API or unauthenticated X-Ray search.
   - **Stage B (Fresh Incognito Extraction):** Extracts structured `Person`, `worksFor`, and `alumniOf` schemas from `<script type="application/ld+json">` with Gaussian jitter, `Referer: https://www.google.com/`, and optional ADB carrier IP rotation.
   - Export any profile as a clean **Markdown CV** or bulk JSON/CSV.

2. **Workflow 2: Cohort & Alumni Shortlister (e.g., RVU 2022 Entrepreneurs)**
   - Filter by compulsory **Institution** (`"RV University"`), **Batch Year** (`"2022"`), and **Role Keywords** (`Founder, Co-Founder, Entrepreneur, Stealth`).
   - Generates compound Boolean X-Ray queries and validates graduation spans (`2018 - 2022`, `2019 - 2022`, or class of `2022`).

3. **Workflow 3: Public Guest Jobs & Entity ID Resolver**
   - Queries `/jobs-guest/jobs/api/seeMoreJobPostings/search` and `/jobs-guest/api/typeaheadHits`.
   - Uses the corrected `f_WT` parameter map (`1=On-site`, `2=Remote`, `3=Hybrid`) and `f_TPR` (`r3600` = 1h, `r86400` = 24h).

4. **Workflow 4: Passive Voyager / HAR Ingest + Chrome Extension**
   - Includes a Manifest V3 Chrome Extension (`chrome-extension/`) that passively listens to `/voyager/api/` JSON responses while you browse normally in Chrome and forwards them to `POST /api/v1/ingest/voyager`—100% undetectable because it makes zero extra requests.

---

## ⚙️ Quick Start

### 1. Backend (FastAPI 0.162.0 + Uvicorn 0.54.0)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

# Optional: Install Patchright chromium binary for deep incognito fallback
# patchright install chromium

# Start Uvicorn (no --reload on Windows to avoid ProactorEventLoop conflicts)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend (Next.js 16.4.1 + pnpm 12.17.0)

```bash
cd frontend
pnpm install
pnpm run security:verify
pnpm dev
```

Open **http://localhost:3000** in your browser.

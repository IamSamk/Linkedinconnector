import csv
import io
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

try:
    from app.database import (
        get_profile_by_slug,
        init_db,
        list_jobs,
        list_profiles,
        upsert_job,
        upsert_profile,
    )
    from app.scraper_engine import (
        build_cohort_xray_query,
        fetch_incognito_profile_cv,
        fetch_public_guest_jobs,
        parse_voyager_normalized_json,
        render_profile_markdown_cv,
        resolve_public_typeahead,
        serper_xray_search,
    )
except ImportError:
    from database import (
        get_profile_by_slug,
        init_db,
        list_jobs,
        list_profiles,
        upsert_job,
        upsert_profile,
    )
    from scraper_engine import (
        build_cohort_xray_query,
        fetch_incognito_profile_cv,
        fetch_public_guest_jobs,
        parse_voyager_normalized_json,
        render_profile_markdown_cv,
        resolve_public_typeahead,
        serper_xray_search,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LinkedIn Public Intelligence & Cohort Discovery API",
    version="2.1.0",
    description="FastAPI 0.162.0 + Uvicorn 0.54.0 backend hardened for post-Black-October 2026 deployments.",
    lifespan=lifespan,
)

cors_origin = os.getenv("CORS_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[cors_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CohortSearchRequest(BaseModel):
    institution: str = Field(default="RV University", description="Compulsory school or organization name")
    batch_year: str = Field(default="2022", description="Graduation or cohort year")
    role_keywords: List[str] = Field(
        default=["Founder", "Co-Founder", "Entrepreneur", "CEO"],
        description="Target role or category keywords",
    )
    location: Optional[str] = Field(default="Bengaluru", description="Optional geographic filter")
    fetch_cv_details: bool = Field(default=True, description="Fetch public JSON-LD CV details after slug discovery")


class JobSearchRequest(BaseModel):
    keywords: str = Field(default="Software Engineer Intern")
    location: str = Field(default="Bengaluru")
    f_WT: Optional[str] = Field(default="1", description="1=On-site, 2=Remote, 3=Hybrid")
    f_TPR: Optional[str] = Field(default="r86400", description="r3600=1h, r86400=24h, r604800=1w")
    f_E: Optional[str] = Field(default="1", description="1=Internship, 2=Entry Level")


@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "ok",
        "fastapi_version": "0.162.0",
        "uvicorn_version": "0.54.0",
        "nextjs_target": "16.4.2",
        "pnpm_target": "12.17.0",
        "security_posture": "Post-Black-October-2026 Hardened (CVE-2026-96889 patched, No LiteLLM, Certifi updated)",
    }


@app.post("/api/v1/csv/upload")
async def upload_bulk_csv(
    file: UploadFile = File(...),
    fetch_cv_details: bool = Query(default=True),
):
    """
    Workflow 1: Upload a bulk CSV of names (columns: name, organization, location, batch).
    Resolves LinkedIn slugs off-platform via X-Ray search and extracts public CV data.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a valid .csv file.")

    content = await file.read()
    decoded = content.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(decoded))

    processed_profiles: List[Dict[str, Any]] = []
    for row in reader:
        name = (row.get("name") or row.get("Name") or "").strip()
        if not name:
            continue
        org = (row.get("organization") or row.get("company") or row.get("school") or "").strip()
        loc = (row.get("location") or "").strip()
        batch = (row.get("batch") or "").strip()

        query_parts = [f'site:linkedin.com/in/ "{name}"']
        if org:
            query_parts.append(f'"{org}"')
        if loc:
            query_parts.append(f'"{loc}"')
        xray_query = " ".join(query_parts)

        hits = await serper_xray_search(xray_query, num_results=3)
        if hits:
            top_hit = hits[0]
            if fetch_cv_details:
                profile = await fetch_incognito_profile_cv(
                    slug=top_hit["slug"],
                    fallback_title=top_hit["title"],
                    fallback_snippet=top_hit["snippet"],
                )
            else:
                profile = {
                    "slug": top_hit["slug"],
                    "full_name": name,
                    "headline": top_hit["title"],
                    "location": loc,
                    "profile_url": top_hit["url"],
                    "summary": top_hit["snippet"],
                    "experiences": [],
                    "educations": [],
                    "skills": [],
                    "source_method": "csv_xray_discovery",
                }
        else:
            fallback_slug = name.lower().replace(" ", "-")
            profile = {
                "slug": fallback_slug,
                "full_name": name,
                "headline": f"{org} ({batch})".strip(),
                "location": loc,
                "profile_url": f"https://www.linkedin.com/in/{fallback_slug}",
                "summary": f"Target queued from CSV ({xray_query}). Add SERPER_API_KEY in .env for live SERP resolution.",
                "experiences": (
                    [{"company": org, "title": "Member / Student", "start_date": "", "end_date": batch, "description": ""}]
                    if org
                    else []
                ),
                "educations": [{"school": org, "degree": "", "start_date": "", "end_date": batch}] if org else [],
                "skills": [],
                "source_method": "csv_queued_target",
            }

        profile["batch_tag"] = batch or "CSV-Upload"
        upsert_profile(profile)
        processed_profiles.append(profile)

    return {
        "processed_count": len(processed_profiles),
        "profiles": processed_profiles,
    }


@app.post("/api/v1/cohort/search")
async def shortlist_cohort(req: CohortSearchRequest):
    """
    Workflow 2: Shortlists users matching compulsory Institution + Batch Year + Role Keywords
    (e.g., RV University 2022 Alumni who are Entrepreneurs).
    """
    xray_query = build_cohort_xray_query(
        institution=req.institution,
        batch_year=req.batch_year,
        role_keywords=req.role_keywords,
        location=req.location,
    )
    hits = await serper_xray_search(xray_query, num_results=10)
    discovered: List[Dict[str, Any]] = []

    for hit in hits:
        if req.fetch_cv_details:
            prof = await fetch_incognito_profile_cv(
                slug=hit["slug"],
                fallback_title=hit["title"],
                fallback_snippet=hit["snippet"],
            )
        else:
            prof = {
                "slug": hit["slug"],
                "full_name": hit["title"].split("-")[0].strip(),
                "headline": hit["title"],
                "location": req.location or "",
                "profile_url": hit["url"],
                "summary": hit["snippet"],
                "experiences": [],
                "educations": [
                    {"school": req.institution, "degree": "Alumni", "start_date": "", "end_date": req.batch_year}
                ],
                "skills": [],
                "source_method": "cohort_xray",
            }
        prof["batch_tag"] = f"{req.institution}-{req.batch_year}"
        upsert_profile(prof)
        discovered.append(prof)

    return {
        "constructed_xray_query": xray_query,
        "google_search_url": f"https://www.google.com/search?q={xray_query.replace(' ', '+')}",
        "results_count": len(discovered),
        "profiles": discovered,
    }


@app.post("/api/v1/ingest/voyager")
async def ingest_passive_voyager_payload(payload: Dict[str, Any]):
    """
    Workflow 4: Parses exported Voyager normalized JSON (`application/vnd.linkedin.normalized+json+2.1`)
    from browser HAR exports.
    """
    extracted = parse_voyager_normalized_json(payload)
    for prof in extracted:
        prof["batch_tag"] = "Voyager-HAR"
        upsert_profile(prof)
    return {
        "ingested_count": len(extracted),
        "profiles": extracted,
    }


@app.get("/api/v1/profiles")
async def get_saved_profiles(batch_tag: Optional[str] = None):
    return {"profiles": list_profiles(batch_tag=batch_tag)}


@app.get("/api/v1/profiles/{slug}/cv-markdown", response_class=PlainTextResponse)
async def download_profile_cv_markdown(slug: str):
    prof = get_profile_by_slug(slug)
    if not prof:
        raise HTTPException(status_code=404, detail="Profile not found in database")
    return render_profile_markdown_cv(prof)


@app.get("/api/v1/export/csv")
async def export_profiles_csv():
    profiles = list_profiles()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["slug", "full_name", "headline", "location", "profile_url", "source_method", "batch_tag", "summary"]
    )
    for p in profiles:
        writer.writerow(
            [
                p["slug"],
                p["full_name"],
                p["headline"],
                p["location"],
                p["profile_url"],
                p["source_method"],
                p["batch_tag"],
                p["summary"],
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=discovered_profiles.csv"},
    )


@app.post("/api/v1/jobs/search")
async def search_public_jobs(req: JobSearchRequest):
    """
    Workflow 3: Queries LinkedIn's unauthenticated /jobs-guest/ API with corrected f_WT mapping.
    """
    jobs = await fetch_public_guest_jobs(
        keywords=req.keywords,
        location=req.location,
        f_WT=req.f_WT,
        f_TPR=req.f_TPR,
        f_E=req.f_E,
    )
    for j in jobs:
        upsert_job(j)
    return {"count": len(jobs), "jobs": jobs}


@app.get("/api/v1/jobs")
async def get_cached_jobs():
    return {"jobs": list_jobs()}


@app.get("/api/v1/typeahead")
async def public_typeahead_lookup(query: str = Query(...), kind: str = Query(default="GEO")):
    hits = await resolve_public_typeahead(query=query, kind=kind)
    return {"query": query, "kind": kind, "hits": hits}
